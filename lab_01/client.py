import socket
import hemming
import random 


HOST = '127.0.0.1'  
PORT = 1700      
random.seed(31132)
BYTE_SIZE = 8

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        input_ = input('Введите "start" для начала раоты. Для выхода введите "exit".\n')
        while input_ != 'exit':
            path = input('Введите путь к файлу с сообщением\n')
            if check_exit(path):
                break
            error_mode = input("""Проверка корректности работы:\n 
            0 - Без ошибок\n 
            1 - С возможными ошибками (не более 1 на слово)\n 
            2 - С множественными ошибками (более 1 на слово, но не обязательно во всех словах)\n""")

            if check_exit(error_mode):
                break
            error_mode = int(error_mode)

            with open(path, 'rb') as f:
                data = f.read() 
            words = hemming.bytes_to_words(data)
            words = [hemming.encode_word(word) for word in words]
            correct_wrds_gen, err_count_gen = insert_errors(words, 0.2, error_mode)
            n = len(words)
            s.sendall(int_to_bytes(n))
            for i, word in enumerate(words):
                s.sendall(word)

            total_err = bytes_to_int(s.recv(BYTE_SIZE))
            correct_words = bytes_to_int(s.recv(BYTE_SIZE))
            print(f'Колличество ошибок, полученное от сервера:  {total_err}') 
            print(f'Количество сгенерированных ошибок: {err_count_gen}')
            print(f'Количество правильно доставленных слов: {correct_words}')
            print(f'Количество неправильно доставленных слов: {n - correct_words}')



def insert_errors(words, worng_word_rate, error_mode):
    correct_words = len(words)
    err_count = 0  
    if error_mode == 0:
        return correct_words, err_count
    elif error_mode == 1:
        for i in range(len(words)):
            if random.random() < worng_word_rate:
                index = random.randint(0, hemming.WORD_LENGTH-1)
                hemming.insert_err(words[i], index)
                correct_words -= 1
                err_count += 1
    else:
        for i in range(len(words)):
            if random.random() < worng_word_rate:
                index1 = random.randint(0, hemming.WORD_LENGTH-1)
                index2 = random.randint(0, hemming.WORD_LENGTH-1)
                if index1 == index2:
                    if index1 > 0:
                        index1 -= 1
                    else:
                        index1 += 1
                hemming.insert_err(words[i], index1)
                hemming.insert_err(words[i], index2)
                correct_words -= 1
                err_count += 2

    return correct_words, err_count



def int_to_bytes(val):
    return val.to_bytes(BYTE_SIZE, byteorder='big')

def bytes_to_int(bytes):
    return int.from_bytes(bytes, byteorder='big', signed=True)

def check_exit(mes):
    return mes == "exit"

main()
