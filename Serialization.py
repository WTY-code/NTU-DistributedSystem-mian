from Global import *
import math


# packed object index format:
# 0 : service ID
# 1 : number of objects, n
# 2 to (n+1) : typeof(obj)
# rest : objects


def marshal(msg):
    numObj = msg[1]
    marshalled = [msg[0], numObj]

    def marshal_and_extend(value, marshal_func):
        marshalled.append(value)
        marshalled.extend(marshal_func(msg[numObj + i]))

    for i in range(2, numObj + 2):
        obj_type = msg[i]
        if obj_type == INT:
            marshal_and_extend(obj_type, marshal_int)
        elif obj_type == STR or obj_type == ERR:
            marshal_and_extend(obj_type, marshal_str)
        elif obj_type == FLT:
            marshal_and_extend(obj_type, marshal_flt)

    return bytes(marshalled)


def unmarshal(msg):
    serviceID = msg[0]
    numObj = msg[1]
    unmarshalled = [serviceID, numObj]
    currentIndex = 2

    def unmarshal_and_append(obj_type, obj_data):
        if obj_type == INT:
            unmarshalled.append(unmarshal_int(obj_data))
        elif obj_type == STR or obj_type == ERR:
            unmarshalled.append(unmarshal_str(obj_data))
        elif obj_type == FLT:
            unmarshalled.append(unmarshal_flt(obj_data))

    for i in range(numObj):
        obj_type = msg[currentIndex]
        len_of_current_obj = msg[currentIndex + 1] + 1
        obj_data = msg[currentIndex + 1: currentIndex + len_of_current_obj]

        unmarshal_and_append(obj_type, obj_data)

        currentIndex += len_of_current_obj

    return unmarshalled


def marshal_int(obj):
    numList = []

    for _ in range(4):
        byte = obj % 256
        numList.append(byte)
        obj = obj // 256

    numList.append(4 + 1)
    numList.reverse()
    return numList


def unmarshal_int(obj):
    num = 0
    for i in range(1, obj[0]):
        num += (obj[i] * int(math.pow(256, len(obj) - i - 1)))
    return num


def marshal_str(obj):
    str_length = len(obj)
    arr = [0] * (str_length + 1)
    arr[0] = str_length + 1

    for i in range(str_length):
        arr[i + 1] = ord(obj[i])

    return arr


def unmarshal_str(obj):
    str_length = obj[0] - 1
    char_list = [chr(obj[i]) for i in range(1, 1 + str_length)]
    return ''.join(char_list)


def marshal_flt(obj):
    return marshal_str(str(obj))


def unmarshal_flt(obj):
    return float(unmarshal_str(obj))
