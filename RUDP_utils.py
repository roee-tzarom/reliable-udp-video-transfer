import struct

# The format for our custom RUDP packet header.
# ! = network byte order
# I = 4 bytes Unsigned Integer (Sequence Number)
# I = 4 bytes Unsigned Integer (Acknowledgment Number)
# c = 1 byte character (Flag: 'S' for SYN, 'A' for ACK, 'D' for DATA, 'F' for FIN)
# H = 2 bytes Unsigned Short (Length of the payload)
MY_RUDP_HEADER_FORMAT = '!IIcH'
HEADER_SIZE = struct.calcsize(MY_RUDP_HEADER_FORMAT)


def create_packet(seq_num, ack_num, flag_char, payload_bytes=b''):
    # This helper function creates the 11-byte header and attaches the data
    payload_length = len(payload_bytes)

    # We pack the variables into binary format
    header = struct.pack(MY_RUDP_HEADER_FORMAT, seq_num, ack_num, flag_char, payload_length)

    # Just simple concatenation of bytes
    full_packet = header + payload_bytes
    return full_packet


def unpack_packet(raw_packet_bytes):
    # This function takes raw bytes from the network and splits them back into readable variables
    if len(raw_packet_bytes) < HEADER_SIZE:
        # Packet is too small, something is wrong
        return None

    # Cut the first 11 bytes for the header
    header_bytes = raw_packet_bytes[0:HEADER_SIZE]

    # Everything else is the actual file data
    payload_bytes = raw_packet_bytes[HEADER_SIZE:]

    # Unpack the header back to variables
    seq_num, ack_num, flag_byte, payload_length = struct.unpack(MY_RUDP_HEADER_FORMAT, header_bytes)

    # Decode the flag from bytes to a regular string so it's easier to use in if-statements
    string_flag = flag_byte.decode('utf-8')

    return seq_num, ack_num, string_flag, payload_length, payload_bytes