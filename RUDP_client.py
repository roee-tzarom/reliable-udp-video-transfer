import socket
import random
import time
from RUDP_utils import create_packet, unpack_packet


class RUDPClient:
    def __init__(self):
        self.my_rudp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.my_rudp_socket.settimeout(5.0)

        # --- THE SIMULATION TOGGLES ---
        # Changed to False for smooth DASH video streaming!
        self.I_WANT_TO_SIMULATE_PACKET_LOSS = False
        self.I_WANT_TO_SIMULATE_LATENCY = False

        self.destination_tuple = None

    def connect(self, server_ip, server_port):
        self.destination_tuple = (server_ip, server_port)
        print("Sending SYN packet to start connection...")

        syn_packet = create_packet(100, 0, b'S')
        self.my_rudp_socket.sendto(syn_packet, self.destination_tuple)

        try:
            raw_received_bytes, _ = self.my_rudp_socket.recvfrom(2048)
            unpacked = unpack_packet(raw_received_bytes)
            if unpacked:
                seq, ack, flag, dlen, payload = unpacked
                if flag == 'A' and ack == 101:
                    print("Got SYN-ACK! Connection is open.")
                    return True
        except socket.timeout:
            print("Connection timed out.")
            return False

    def fetch_dash_chunk(self, url_to_download):
        my_command = f"FETCH {url_to_download}".encode('utf-8')
        command_packet = create_packet(101, 0, b'D', my_command)
        self.my_rudp_socket.sendto(command_packet, self.destination_tuple)

        try:
            self.my_rudp_socket.recvfrom(2048)
            print(f"Server acknowledged FETCH for {url_to_download}. Downloading silently...")
        except socket.timeout:
            print("Server didn't ACK the command.")
            return b''

        all_file_bytes = b''
        the_chunk_i_am_expecting = 1

        while True:
            try:
                incoming_packet, _ = self.my_rudp_socket.recvfrom(2048)
                unpacked = unpack_packet(incoming_packet)
                if not unpacked:
                    continue

                inc_seq, inc_ack, string_flag, inc_len, inc_payload = unpacked

                if string_flag == 'D':
                    if self.I_WANT_TO_SIMULATE_LATENCY:
                        time.sleep(random.uniform(0.1, 0.4))

                    if self.I_WANT_TO_SIMULATE_PACKET_LOSS:
                        if random.random() < 0.3:
                            # print(f"SIMULATING PACKET LOSS! Dropping Chunk {inc_seq}")
                            continue

                    if inc_seq == the_chunk_i_am_expecting:
                        all_file_bytes = all_file_bytes + inc_payload
                        the_chunk_i_am_expecting = the_chunk_i_am_expecting + 1

                        my_ack_packet = create_packet(0, inc_seq, b'A')
                        self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)
                    else:
                        last_good_chunk = the_chunk_i_am_expecting - 1
                        # print(f"Out of order. Wanted {the_chunk_i_am_expecting}, got {inc_seq}. Resending ACK {last_good_chunk}.")
                        my_ack_packet = create_packet(0, last_good_chunk, b'A')
                        self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)

                elif string_flag == 'F':
                    print("Server sent FIN. Chunk transfer completed.")
                    my_ack_packet = create_packet(0, inc_seq, b'A')
                    self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)
                    break

            except socket.timeout:
                print("The socket timed out while receiving data.")
                break

        return all_file_bytes

    def close(self):
        self.my_rudp_socket.close()


# בלוק ההרצה נשאר בחוץ, בלי רווחים!
if __name__ == "__main__":
    print("Starting RUDP Client Test...")
    client = RUDPClient()
    connected = client.connect("127.0.0.1", 2122)

    if connected:
        print("\n--- Requesting Video Chunk ---")
        downloaded_data = client.fetch_dash_chunk("http://127.0.0.1:8080/video_720p.mp4")
        print(f"\nSUCCESS! Downloaded a total of {len(downloaded_data)} bytes.")

    client.close()