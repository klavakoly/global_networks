import math


WORD_LENGTH = 77
K = 7
BYTE_SIZE = 8

def insert_zero_cbits(word, msg_len):
    sstart = 0
    k = 2
    dst = bytearray(math.ceil(msg_len / BYTE_SIZE))

    while k < msg_len:
        i = k
        j = min(msg_len, 2*k-1)
        count = j - i
        write_bits(dst, word, i, sstart, count)
        sstart += count
        k *= 2

    return dst



def calculate_control_bits(barr, k, msg_len):
    control_bits = []

    for control_bit in range(k):
        n = 2**control_bit
        t = 0
        for i in range(n-1, msg_len, 2*n):
            upper_bound = min(i+n, msg_len)
            for j in range(i, upper_bound):
                byte_index = j // BYTE_SIZE
                bit_index = j % BYTE_SIZE
                mask = 128 >> bit_index

                if mask & barr[byte_index] > 0:
                    t = t ^ 1

        control_bits.append(t)
    
    return control_bits



def set_control_bits(barr, k, control_bits):
    c_bit_pos = 1
    for i in range(k):
        byte_pos = (c_bit_pos-1) // BYTE_SIZE
        bit_pos = (c_bit_pos-1) % BYTE_SIZE

        v = barr[byte_pos]
        mask = 128 >> bit_pos
        cbit = control_bits[i] << (7 - bit_pos)
        barr[byte_pos] = (v & ~mask) | cbit

        c_bit_pos *= 2



def calculate_parity_bit(word, msg_len):
    t = 0
    for i in range(msg_len):
        byte_index = i // BYTE_SIZE
        bit_index = i % BYTE_SIZE
        mask = 128 >> bit_index
        bit = 0
        if (word[byte_index] & mask) > 0:
            bit = 1
        t = t ^ bit
    
    return t



def insert_parity_bit(word, msg_len, bit):
    if msg_len == len(word) * BYTE_SIZE:
        word = word + bytearray.fromhex('00')
    
    byte_pos = msg_len // BYTE_SIZE
    bit_pos = msg_len % BYTE_SIZE

    v = word[byte_pos]
    mask = 128 >> bit_pos
    word[byte_pos] = (~mask & v) | (bit << (7 - bit_pos))
    
    return word



def get_main_data(msg):
    byte_count = math.ceil(WORD_LENGTH / BYTE_SIZE)
    res = bytearray(byte_count)
    res_bits_count = 0

    total_msg_len = WORD_LENGTH + K
    block_start = 2
    while block_start < total_msg_len:
        block_end = min(total_msg_len, block_start*2 - 1)
        count = block_end - block_start
        write_bits(res, msg, res_bits_count, block_start, count)
        res_bits_count += count
        block_start *= 2

    return res



def get_parity_bit(word, msg_len):
    byte_pos = msg_len // BYTE_SIZE
    bit_pos = msg_len % BYTE_SIZE
    
    bit = 0
    mask = 128 >> bit_pos
    if word[byte_pos] & mask > 0:
        bit = 1

    return bit



def encode_word(word):
    word = insert_zero_cbits(word, WORD_LENGTH + K)
    control_bits = calculate_control_bits(word, K, WORD_LENGTH)
    set_control_bits(word, K, control_bits)

    msg_len = WORD_LENGTH + K
    bit = calculate_parity_bit(word, msg_len)
    word = insert_parity_bit(word, msg_len, bit)

    return word



def decode_word(word):
    msg_len = WORD_LENGTH + K
    bits = calculate_control_bits(word, K, WORD_LENGTH)
    p_extr = get_parity_bit(word, msg_len)
    p_calc = calculate_parity_bit(word, WORD_LENGTH + K)
    p = p_calc^p_extr

    control_number = 0
    for i, b in enumerate(bits):
        if b:
            control_number += 2**i
    

    if control_number == 0:
        return get_main_data(word), 0
    elif control_number != 0 and p == 1:
        control_number -= 1
        byte_pos = control_number // BYTE_SIZE
        bit_pos = control_number % BYTE_SIZE

        v = word[byte_pos]
        mask = 128 >> bit_pos
        bit = 1
        if v & mask > 0:
            bit = 0

        word[byte_pos] = (~mask & v) | (bit << (7-bit_pos))
        return get_main_data(word), 1

    return word, 2



def write_bits(dst, src, dstart, sstart, count):
    dst_pos = dstart
    src_pos = sstart

    for i in range(count):
        dst_byte_pos = dst_pos // BYTE_SIZE
        dst_bit_pos = dst_pos % BYTE_SIZE
        src_byte_pos = src_pos // BYTE_SIZE
        src_bit_pos = src_pos % BYTE_SIZE
        
        dst_mask = 128 >> dst_bit_pos
        src_mask = 128 >> src_bit_pos
        
        v = src_mask & src[src_byte_pos]
        v = v << src_bit_pos
        v = v >> dst_bit_pos
        dst[dst_byte_pos] = (~dst_mask & dst[dst_byte_pos]) | v
        
        dst_pos += 1
        src_pos += 1
    


def insert_err(word, index):
    byte_pos = index // BYTE_SIZE
    bit_pos = index % BYTE_SIZE
    mask = 128 >> bit_pos
    bit = 1
    if word[byte_pos] & mask > 0:
        bit = 0
    word[byte_pos] = (~mask & word[byte_pos]) | (bit << (7 - bit_pos) )



def bytes_to_words(data):
    words = []
    n = math.ceil(len(data) * BYTE_SIZE / WORD_LENGTH)
    WORD_LENGTH_in_bytes = math.ceil(WORD_LENGTH / BYTE_SIZE)

    data_pos = 0
    for i in range(n):
        word = bytearray(WORD_LENGTH_in_bytes)
        count = min(WORD_LENGTH, len(data) - i*WORD_LENGTH)
        write_bits(word, data, 0, data_pos, count)
        data_pos += WORD_LENGTH
        words.append(word)
    
    return words