import socket
import os
import sys
import threading
import time
import stat
import authorization as au
from utils import fileProperty
import shutil


ENCODING = 'utf-8'

class FTPThreadServer(threading.Thread):
    def __init__(self, conn, au):
        self.cwd = os.getcwd()
        self.authenticated = False
        self.datasock = None
        self.login = None
        self.password = None
        self.client = conn[0]
        self.client_adr = conn[1]
        self.pasv_mode = False
        self.pasv_sock = None
        self.au = au
        
        threading.Thread.__init__(self)

    def run(self):
        try:
            print(f'client connected {self.client_adr}')
            self.client.send('220 Welcome.\r\n'.encode(ENCODING))
            while True:
                cmd = self.client.recv(1024)
                if not cmd:
                    break
                cmd = cmd.decode(ENCODING)
                print('cmd ' + cmd)
                try:
                    func = getattr(self, cmd[:4].strip().upper())
                    func(cmd)
                except AttributeError as e:
                    print(f'ERROR: {e} : Invalid Command.')
                    self.client.send('550 Invalid Command\r\n'.encode(ENCODING))
        except Exception as e:
            print('ERROR: ' + str(e))
            self.QUIT('')

    def QUIT(self, cmd):
        try:
            response = '221 Goodbye'
            response += '\r\n'
            self.client.send(response.encode(ENCODING))
        except Exception as e:
            print(e)
        finally:
            print(f'Closing connection from  {self.client_adr}')
            self.client.close()
            quit()

    def HELP(self, cmd):
        try:
            #response = self.__dir__()
            #response = '\r\n'.join(
            #    [e for e in response if all([el.isupper() for el in e])])
            #response += '\r\n'
            response = """QUIT \r\nUSER \r\nPASS \r\nPWD \r\nCWD \r\nMKD \r\nRMD \r\nPORT \r\nPASV \r\nLIST \r\nSTOR \r\nRETR \r\n"""
            self.client.send(response.encode(ENCODING))
        except Exception as e:
            print(e)


    def USER(self, cmd):
        self.login = cmd[4:].strip()
        self.client.send('331 need password \r\n'.encode(ENCODING))


    
    def PASS(self, cmd):
        self.password = cmd[4:].strip()
        if self.au.isAuthorized(self.login, self.password):
            self.authenticated = True
            self.client.send('200 logged in\r\n'.encode(ENCODING))
        else:
            self.client.send('500 incorrect login or password\r\n'.encode(ENCODING))

    def PWD(self, cmd):
        response = f'257 \"{self.cwd}\".\r\n'
        self.client.send(response.encode())

    def CWD(self, cmd):
        dest = os.path.join(self.cwd, cmd[4:].strip())
        if (os.path.isdir(dest)):
            self.cwd = os.path.normpath(dest)
            response = f'250 OK \"{self.cwd}\".\r\n'
            self.client.send(response.encode())
        else:
            er = 'ERROR: ' + str(self.client_adr) + \
                ': No such file or directory.'
            print(er.encode())
            response = '550 \"' + dest + '\": No such file or directory.\r\n'
            self.client.send(response.encode())

    def CDUP(self, cmd):
        dest = os.path.abspath(os.path.join(self.cwd, '..'))
        if (os.path.isdir(dest)):
            self.cwd = dest
            response = '250 OK \"{self.cwd}\".\r\n'
            self.client.send(response.encode())
        else:
            er = 'ERROR: ' + str(self.client_address) + \
                ': No such file or directory.'
            print(er.encode())
            response = '550 \"' + dest + '\": No such file or directory.\r\n'
            self.client.send(response.encode())

    def MKD(self, cmd):
        path = cmd[4:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not self.authenticated:
                response = '530 User not logged in.\r\n'
                self.client.send(response.encode())
            elif not path:
                response = '501 Missing arguments <dirname>.\r\n'
                self.client.send(response.encode())
            else:
                os.mkdir(dirname)
                response = '250 Directory created: ' + dirname + '.\r\n'
                self.client.send(response.encode())
        except Exception as e:
            er = 'ERROR: ' + str(self.client_address) + ': ' + str(e)
            print(er.encode())
            response = '550 Failed to create directory ' + dirname + '.'
            self.client.send(response.encode())

    def RMD(self, cmd):
        if not self.authenticated:
            self.client.send('530 User not logged in.\r\n'.encode(ENCODING))
            return

        path = cmd[4:].strip()
        dirname = os.path.join(self.cwd, path)
        try:
            if not path:
                response = '501 Missing arguments <dirname>.\r\n'
                self.client.send(response.encode())
            else:
                shutil.rmtree(dirname)
                response = '250 Directory deleted: ' + dirname + '.\r\n'
                self.client.send(response.encode())
        except Exception as e:
            er = 'ERROR: ' + str(self.client_adr) + ': ' + str(e)
            print(er.encode())
            response = '550 Failed to delete directory ' + dirname + '.'
            self.client.send(response.encode())
  
        
    def PORT(self, cmd):
        try:
            l=cmd[4:].strip()
            l = l[l.index('(') + 1: l.index(')')]
            l = l.split(',')
            adress = '.'.join(l[:4])
            port = 256 * int(l[4]) + int(l[5]) 
            self.dataSockAddr= adress
            self.dataSockPort= port
            self.client.send('200 Get port.\r\n'.encode(ENCODING))
            if self.pasv_mode:
                self.finalizePasvSock()
                self.pasv_mode = False
        except Exception as err:
            self.client.send('500 wrong adress.\r\n'.encode(ENCODING))

    def PASV(self, cmd):
        try:
            self.pasv_sock = create_server_sock(('', 0))
            adr, port = self.pasv_sock.getsockname()
            hp = port // 256
            lp = port - hp*256
            data = f'({adr.replace(".", ",")},{hp},{lp})'
            self.client.send(f'200 {data}\r\n'.encode(ENCODING))
            self.pasv_mode = True
            
        except Exception as err:
            self.finalizePasvSock()
            print(err)
    
    def LIST(self, cmd):
        cmd = cmd[4:].strip()
        if not self.authenticated:
            self.client.send('530 User not logged in.\r\n'.encode(ENCODING))
            return

        if not cmd:
            pathname = self.cwd
        elif cmd.startswith(os.path.sep) or ':\\' in cmd:
            pathname = os.path.normpath(cmd)
        else:
            pathname = os.path.normpath(os.path.join(self.cwd, cmd))

        print(pathname)
        if not self.authenticated:
            self.client.send('530 User not logged in.\r\n'.encode(ENCODING))

        elif not os.path.exists(pathname):
            self.client.send('550 LIST failed Path name not exists.\r\n'.encode(ENCODING))

        else:
            self.client.send('150 Here is listing.\r\n'.encode(ENCODING))
            self.startDataSock( )

            if not os.path.isdir(pathname):
                fileMessage = fileProperty(pathname)
                self.datasock.send((fileMessage+'\r\n').encode(ENCODING))
            else:
                for file in os.listdir(pathname):
                    fileMessage = fileProperty(os.path.join(pathname, file))
                    self.datasock.send((fileMessage+'\r\n').encode(ENCODING))

            #list_dir = '\n'.join(os.listdir(pathname))
            #list_dir += '\r\n'
            #self.datasock.send(list_dir.encode(ENCODING))

            self.finalizeDataSock()
            self.client.send('226 List done.\r\n'.encode(ENCODING))


    def STOR(self, cmd):
        path = cmd[4:].strip()

        if not self.authenticated:
            self.client.send('530 User not logged in.\r\n'.encode(ENCODING))
            return

        if not path:
            self.client.send('501 Missing arguments <filename>.\r\n'.encode(ENCODING))
            return

        fname = os.path.normpath(os.path.join(self.cwd, path))
        self.client.send('200 Here is a file.\r\n'.encode(ENCODING))
        self.startDataSock()

        try:
            file_write = open(fname, 'wb')
            while True:
                data = self.datasock.recv(1024)
                if not data:
                    break
                file_write.write(data)

            self.client.send('226 Transfer complete.\r\n'.encode(ENCODING))
        except Exception as e:
            print('ERROR: ' + str(self.client_adr) + ': ' + str(e))
            self.client.send('425 Error writing file.\r\n'.encode(ENCODING))
        finally:
            file_write.close()
            self.finalizeDataSock()

    def RETR(self, cmd):
            path = cmd[4:].strip()
     
            if not path:
                self.client.send('501 Missing arguments <filename>.\r\n'.encode(ENCODING))
                return

            basename = os.path.basename(path)
            fname = os.path.normpath(os.path.join(self.cwd, basename))

            if not os.path.exists(fname):
                self.client.send('500 no such file.\r\n'.encode(ENCODING))
                return

            self.client.send('200 Transfer starts.\r\n'.encode(ENCODING))
            self.startDataSock()

            try:
                file = open(fname, 'rb')
                while True:
                    data = file.read(1024)
                    self.datasock.send(data)
                    if not data:
                        break

                self.client.send('226 Transfer complete.\r\n'.encode(ENCODING))
            except Exception as e:
                print('ERROR: ' + str(self.client_adr) + ': ' + str(e))
                self.client.send('425 Error writing file.\r\n'.encode(ENCODING))
            finally:
                file.close()
                self.finalizeDataSock()

    def finalizeDataSock(self):
        if self.datasock != None:
            self.datasock.close()
            self.datasock= None

        self.finalizePasvSock()

    def finalizePasvSock(self):
        if self.pasv_sock != None:
            self.pasv_sock.close()
            self.pasv_sock = None
            
    def startDataSock(self):
        if self.pasv_mode:
            self.datasock, adr = self.pasv_sock.accept()
            print(f'pasv conn from {adr}')
        else:
            print((self.dataSockAddr, self.dataSockPort))
            self.datasock = socket.create_connection((self.dataSockAddr, self.dataSockPort))


class FTPserver:
    def __init__(self, port):
        # server address at localhost
        self.address = '0.0.0.0'
        self.port = port
        self.au = au.defaultAuthorization()

    def start_sock(self):
        # create TCP socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = (self.address, self.port)

        try:
            print('Creating data socket on',
                  self.address, ':', self.port, '...')
            self.sock.bind(server_address)
            self.sock.listen(5)
            print('Server is up. Listening to', self.address, ':', self.port)
        except Exception as e:
            print('Failed to create server on', self.address,
                  ':', self.port, 'because', str(e.strerror))
            quit()


    def start(self):
        self.start_sock()

        try:
            while True:
                print('Waiting for a connection')
                thread = FTPThreadServer(self.sock.accept(), self.au)
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print('Closing socket connection')
            self.sock.close()
            quit()


def main():
    port = input("Port - if left empty, default port is 2121: ")
    if not port:
        port = 2121
    else:
        port = int(port)
    server = FTPserver(port)
    server.start()

def create_server_sock(adr=('',0)):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(adr)
    sock.listen()
    return sock

main()
