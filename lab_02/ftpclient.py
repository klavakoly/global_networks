# simple FTP client
# commands
#        LIST <arg>, information of a directory or file,
#                     or information of current remote directory if not specified
#        STOR <file_name>, copy file to current remote directory
#     RETR <file_name>, retrieve file from current remote directory
# additional commands
#        PWD, get current remote directory
#        CDUP, change to parent remote directory
#        CWD <arg>, change current remote directory
#        MKD, make a directory in remote server
#        RMD <dir_name>, remove a directory in remote server
#        DELE <file_name>, delete a file in remote server

import socket
import os
import sys
import logging



log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.FATAL)

DEFAULT_PORT = 21
DEFAULT_ENCODING = 'utf-8'
MAX_BUFF_SIZE = 4096



class FTPclient:
    def __init__(self):
        self.command_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.datasock = None

        self.run = False
        self.pasv_mode = False
        self.allowed_commands = self.__get_allowed_commands()
        self.srv_sock = None
        self.pasv_params = None
        # TODO
        #hostname = socket.gethostname()
        #self.hostip = socket.gethostbyname(hostname)
        self.hostip = '127.0.0.1'

    def QUIT(self, arg):
        resp = self.__execute_command('QUIT', arg)
        self.close_client()
        self.run = False
        return resp, ''

    def LIST(self, arg):
        err = self.setup_datasock_mod()

        if err:
            self.__data_sock_finilize()
            return err, ''

        resp = self.__execute_command('LIST', arg)

        status = self.__extract_status(resp)
        ok = status[0] == '1' or status[0] == '2'
        if not ok:
            self.__data_sock_finilize()
            return resp, ''
        
        self.__connect_datasock()
        if self.datasock is None:
            self.__data_sock_finilize()
            return resp, 'datasock error'
        
        dirlist = ''
        try:
            while True:
                temp = self.datasock.recv(MAX_BUFF_SIZE)
                if not temp:
                    break
                dirlist = dirlist + temp.decode(DEFAULT_ENCODING)

            self.command_sock.recv(MAX_BUFF_SIZE)
        except Exception as e:
            log.error(e)
        finally:
            self.__data_sock_finilize()
            return dirlist, ''

    def HELP(self, arg):
        resp = self.__execute_command('HELP', arg)
        return resp, ''

    def USER(self, arg):
        resp = self.__execute_command('USER', arg)
        return resp, ''

    def PWD(self, arg):
        resp = self.__execute_command('PWD', arg)
        return resp, ''
    
    def CWD(self, arg):
        resp = self.__execute_command('CWD', arg)
        return resp, ''

    def PASS(self, arg):
        resp = self.__execute_command('PASS', arg)
        return resp, ''

    def PASV(self, arg):
        resp = self.__execute_command('PASV', arg)
        status = self.__extract_status(resp)

        if status[0] == '2':
            self.pasv_mode = True
            start = resp.index('(') + 1
            end = resp.index(')')
            resp = resp[start : end]
            resp = resp.split(',')
            port = int(resp[-2]) << 8 + int(resp[-1])
            adr = '.'.join(resp[:-2])
            log.info('passive mode choosen')

            return resp, (adr, port)
        
        return resp, ('', 0)

    def PORT(self, arg):
        arg_ = self.hostip.split('.')
        port = int(arg)
        port_up = port // 256
        arg_ += [str(port_up), str(port - port_up * 256)]
        arg = ','.join(arg_)
        arg = f'({arg})'
        resp = self.__execute_command('PORT', arg)
        
        status = self.__extract_status(resp)
        if status[0] == '2':
            self.pasv_mode = False
            log.info('active mode choosen')
            return resp, 'ok'

        return resp, 'error'

    def RETR(self, arg):
        err = self.setup_datasock_mod()

        if err:
            self.__data_sock_finilize()
            return err, ''

        resp = self.__execute_command('RETR', arg)

        status = self.__extract_status(resp)
        ok = status[0] == '1' or status[0] == '2'
        if not ok:
            self.__data_sock_finilize()
            return resp, ''
        
        self.__connect_datasock()
        if self.datasock is None:
            self.__data_sock_finilize()
            return resp, 'datasock error'
        
        path = self.__gen_file_name(os.path.basename(arg)) 
        status = 'something went wrong'      
        try:
            with open(path, 'wb') as f:
                log.debug('file has opend')
                while True:
                    temp = self.datasock.recv(MAX_BUFF_SIZE)
                    log.debug(f'block has been read : {len(temp)}')
                    if not temp:
                        break
                    f.write(temp)
                    log.debug(f'block has been wrote : {len(temp)}')

            status = self.command_sock.recv(MAX_BUFF_SIZE).decode(DEFAULT_ENCODING)
        except Exception as e:
            log.error(e)
        finally:
            self.__data_sock_finilize()
            return status, ''

    def STOR(self, arg):
        if not os.path.exists(arg):
            return 'file does not exist', ''
        err = self.setup_datasock_mod()

        if err:
            self.__data_sock_finilize()
            return err, ''

        resp = self.__execute_command('STOR', arg)

        status = self.__extract_status(resp)
        ok = status[0] == '1' or status[0] == '2'
        if not ok:
            self.__data_sock_finilize()
            return resp, ''
        
        self.__connect_datasock()
        if self.datasock is None:
            self.__data_sock_finilize()
            return resp, 'datasock error'
        
        path = arg
        status = 'something went wrong'      
        try:
            with open(path, 'rb') as f:
                log.debug('file has opend')
                while True:
                    temp = f.read(MAX_BUFF_SIZE)
                    log.debug(f'block has been read : {len(temp)}')
                    self.datasock.send(temp)
                    log.debug(f'block has been wrote : {len(temp)}')
                    if not temp:
                        break
            self.datasock.close()
            self.datasock = None
            status = self.command_sock.recv(MAX_BUFF_SIZE).decode(DEFAULT_ENCODING)
        except Exception as e:
            log.error(e)
        finally:
            self.__data_sock_finilize()
            return status, ''

    def MKD(self, arg):
        resp = self.__execute_command('MKD', arg)
        return resp, ''

    def TYPE(self, arg):
        resp = self.__execute_command('TYPE', arg)
        return resp, ''
    def RMD(self, arg):
        resp = self.__execute_command('RMD', arg)
        return resp, ''

    def DELE(self, arg):
        resp = self.__execute_command('DELE', arg)
        return resp, ''

    def close_client(self):
        print('Closing socket connection...')
        self.command_sock.close()

    def setup_datasock_mod(self):
        self.srv_sock = self.__open_srv_sock()
        _, status = self.PORT(self.srv_sock.getsockname()[1])
        if status == 'ok':
            return ''

        resp, (host, port) = self.PASV('')
        if host != '' and port > 0:
            self.pasv_params = (host, port)
            return ''

        return 'cannot setup data mode'
        
    def is_command_allowed(self, command):
        return command in self.allowed_commands

    def connect(self, address, port):
        self.__connect(address, port)
        self.run = True

        while self.run:
            try:
                command = input('Enter command: ')
                cmd = command[:4].strip().upper()
                arg = command[4:].strip()

            except KeyboardInterrupt:
                self.close_client()

            if not self.is_command_allowed(cmd):
                print('command is not supported. Use HELP to list allowed commands')
                continue

            cmd_hndl = getattr(self, cmd)
            resp, handler_resp = cmd_hndl(arg)
            print(resp)
    
        print('FTP client terminating...')
    
    def __gen_file_name(self, base):
        if not os.path.exists(base):
            return base

        i = 1
        base = base.split('.')
        base, fmt = '.'.join(base[:-1]), base[-1]
        while True:
            name = f'{base}({i}).{fmt}'
            if not os.path.exists(name):
                return name
            i += 1

    def __execute_command(self, cmd, arg):
        log.debug(f'executing command {cmd} {arg}')
        try:
            command = f'{cmd} {arg}'.strip()
            self.command_sock.send(bytes(command, DEFAULT_ENCODING))
            log.debug(f'command sent')

            resp = self.command_sock.recv(MAX_BUFF_SIZE).decode(DEFAULT_ENCODING)
            log.debug(f'executing command recived {resp}')
            return resp

        except Exception as e:
            log.error(e)
            self.close_client()

    def __get_allowed_commands(self):
        return [ command for command in self.__dir__() if all([l.isupper() for l in command]) ]

    def __connect(self, address, port):
        adr = (address, port)
        print('Starting connection to', address, ':', port)

        try:
            self.command_sock.connect(adr)
            msg = self.command_sock.recv(MAX_BUFF_SIZE)
            print('Connected to', address, ':', port)
            print(msg.decode(DEFAULT_ENCODING))
        
        except KeyboardInterrupt:
            self.close_client()
        except Exception as err:
            print(f'Connection to {address}:{port} failed : {err}')
            self.close_client()

    def __extract_status(self, resp):
        return resp[:3]

    def __connect_datasock(self):
        try:
            if self.pasv_mode:
                _, adr = self.PORT('')
                self.datasock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.datasock.connect(adr)
            
            else:
                self.datasock, adr = self.srv_sock.accept()
                log.info(f'dataconnection from {adr}')

        except Exception as err:
            self.datasock = None
            if self.srv_sock:
                self.srv_sock.close()
                self.srv_sock = None

            print(f'datasock connection error : {err}')

    def __write_file(self, data, path):
        if os.path.exists(path):
            return 'path already exists'
        
        with open(path, 'w') as f:
            f.write(data)
        
        return f'dumped to {path}'

    def __data_sock_finilize(self):
        if self.datasock:
            self.datasock.close()
            self.datasock = None
            log.info('datasock has closed')
        
        if self.srv_sock:
            self.srv_sock.close()
            self.srv_sock = None
            log.info('srv_sock has closed')

    def __open_srv_sock(self):
        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv_sock.bind(('', 0))
        srv_sock.listen()
        return srv_sock


def main():
    address = input(
        "Destination address - if left empty, default address is localhost: ")

    if not address:
        address = 'localhost'

    port = input(f'Port - if left empty, default port is {DEFAULT_PORT}: ')
    port = int(port)

    if not port:
        port = DEFAULT_PORT

    ftpClient = FTPclient()
    ftpClient.connect(address, port)


main()
