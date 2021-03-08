import socket
import hemming
import math


HOST = '127.0.0.1'
PORT = 1700
BYTE_SIZE = 8

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        conn, addr = s.accept()
        with conn:
            print('Connected by', addr)
            while True:
                n = conn.recv(BYTE_SIZE)
                n = bytes_to_int(n)
                total_err_count = 0
                total_correct_words = 0
                msg_size = math.ceil((hemming.WORD_LENGTH + hemming.K) / BYTE_SIZE)

                for i in range(n):
                    word = conn.recv(msg_size)
                    word = bytearray(word)
                    _, err_c = hemming.decode_word(word)
                    total_err_count += err_c
                    if err_c  < 2:
                        total_correct_words += 1

                conn.sendall(int_to_bytes(total_err_count))
                conn.sendall(int_to_bytes(total_correct_words))
                
def int_to_bytes(val):
    return val.to_bytes(8, byteorder='big')

def bytes_to_int(bytes):
    return int.from_bytes(bytes, byteorder='big', signed=True)
    
main()