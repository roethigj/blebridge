from typing import List

import dbus


def check_flags(flags: List[str]):
    """
    Helper function that checks if the given flags are supported by BlueZ.
    Supported flags at the moment are:
    * read
    * write
    * notify

    Args:
        flags (List[str]): input list of flags

    Raises:
        ValueError: unsupported flag is given
    """

    for flag in flags:
        if flag not in ["read", "write", "notify"]:
            raise ValueError("unknown flag")


def byte_arr_to_str(byte_array: dbus.Array) -> str:
    """
    Helper function that converts dbus byte array to an ascii string.
    Args:
        byte_array (dbus.Array): Byte array to be decoded to a string

    Returns:
        str: converted byte array
    """
    byte_list = [bytes([v]) for v in byte_array]
    try:
        decoded_list = [str(v, "ascii") for v in byte_list]
        # Returns the array as a single string
        final_string = "".join(decoded_list)
    except Exception:
        raise ValueError
    return final_string


def str_to_byte_arr(text: str) -> dbus.Array:
    """
    Helper function that a string to dbus byte array using ascii encoding.
    Args:
        text (String): String to convert to array
    Returns:
        dbus.Array: byte array
    """

    ascii_values = dbus.Array([], signature=dbus.Signature("y"))
    for character in text:
        ascii_values.append(dbus.Byte(ord(character)))
    return ascii_values
