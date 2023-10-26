from Global import *
import math


# packed object index format:
# 0 : service ID
# 1 : number of objects, n
# 2 to (n+1) : typeof(obj)
# rest : objects


def marshal(msg):
    # Extract the number of objects (numObj) from the input 'msg' and initialize a 'marshalled' list
    numObj = msg[1]
    marshalled = [msg[0], numObj]

    # Define a helper function 'marshal_and_extend' to marshal and extend the 'marshalled' list
    # This function takes a 'value' and a 'marshal_func' to encode and add values to the 'marshalled' list
    def marshal_and_extend(value, marshal_func):
        marshalled.append(value)
        marshalled.extend(marshal_func(msg[numObj + i]))

    # Iterate through the objects in the 'msg' starting from index 2
    for i in range(2, numObj + 2):
        # Based on the object type, marshal and extend the 'marshalled' list using appropriate functions
        obj_type = msg[i]
        if obj_type == INT:
            marshal_and_extend(obj_type, marshal_int)
        elif obj_type == STR or obj_type == ERR:
            marshal_and_extend(obj_type, marshal_str)
        elif obj_type == FLT:
            marshal_and_extend(obj_type, marshal_flt)

    # Convert the 'marshalled' list to bytes and return the marshalled message for transmission
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
    numList = []    # Create an empty byte list to store the marshaled data

    for _ in range(4):  # Assuming the integer occupies 4 bytes
        byte = obj % 256    # Extract the lowest 8 bits of the integer using bitwise AND
        numList.append(byte)    # Add the extracted byte to the list
        obj = obj // 256    # Right-shift the integer to process the next byte

    numList.append(4 + 1)   # Add a byte to represent the length of the integer (4 bytes + 1 byte)
    numList.reverse()   # Reverse the byte list to ensure correct byte order
    return numList  # Return the marshaled byte list


def unmarshal_int(obj):
    num = 0
    for i in range(1, obj[0]):
        num += (obj[i] * int(math.pow(256, len(obj) - i - 1)))
    return num


def marshal_str(obj):
    # Calculate the length of the input string and store it in the 'str_length' variable
    str_length = len(obj)
    # Create a list 'arr' of length 'str_length + 1' to store the marshalled string
    arr = [0] * (str_length + 1)
    # Set the first element of 'arr' (index 0) to 'str_length + 1' to store the length of the string
    arr[0] = str_length + 1

    # Iterate through each character of the input string
    for i in range(str_length):
        # Store the ASCII value of the current character in 'arr' starting from index 1
        arr[i + 1] = ord(obj[i])

    # Return the 'arr' list containing the encoded string with length information
    return arr


def unmarshal_str(obj):
    str_length = obj[0] - 1
    char_list = [chr(obj[i]) for i in range(1, 1 + str_length)]
    return ''.join(char_list)


def marshal_flt(obj):
    # Convert the input 'obj' (a floating-point number) to a string, then encode it using 'marshal_str'
    return marshal_str(str(obj))


def unmarshal_flt(obj):
    return float(unmarshal_str(obj))
