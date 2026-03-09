import socket
import urllib.request
from RUDP_utils import create_packet, unpack_packet


class RUDPServer:
    def __init__(self, ip='127.0.0.1', port=2122):
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.my_socket.bind((ip, port))

        self.MAX_WINDOW_LIMIT = 5
        print(f"RUDP Server is up and listening on {ip}:{port}")

    def serve_data(self, file_bytes, client_address):
        chunks_list = []
        current_idx = 0
        while current_idx < len(file_bytes):
            one_chunk = file_bytes[current_idx: current_idx + 500]
            chunks_list.append(one_chunk)
            current_idx = current_idx + 500

        total_chunks = len(chunks_list)
        print(f"Prepared {total_chunks} chunks for sending. Transfer in progress...")

        current_window_size = 1
        oldest_unacked_chunk = 1
        next_chunk_to_send = 1

        while oldest_unacked_chunk <= total_chunks:
            right_edge_of_window = oldest_unacked_chunk + current_window_size - 1
            if right_edge_of_window > total_chunks:
                right_edge_of_window = total_chunks

            while next_chunk_to_send <= right_edge_of_window:
                chunk_data = chunks_list[next_chunk_to_send - 1]
                packet = create_packet(next_chunk_to_send, 0, b'D', chunk_data)
                self.my_socket.sendto(packet, client_address)
                # print(f"Sent chunk {next_chunk_to_send}") # המושתק
                next_chunk_to_send = next_chunk_to_send + 1

            self.my_socket.settimeout(1.0)
            try:
                ack_raw, _ = self.my_socket.recvfrom(2048)
                unpacked = unpack_packet(ack_raw)

                if unpacked:
                    seq, ack_num, flag, dlen, payload = unpacked

                    if flag == 'A' and ack_num >= oldest_unacked_chunk:
                        # print(f"Got ACK for chunk {ack_num}!") # המושתק
                        oldest_unacked_chunk = ack_num + 1

                        if current_window_size < self.MAX_WINDOW_LIMIT:
                            current_window_size = current_window_size + 1

            except socket.timeout:
                print("\nTIMEOUT! Packet lost. Slapping brakes on the network.")
                current_window_size = current_window_size // 2
                if current_window_size < 1:
                    current_window_size = 1
                next_chunk_to_send = oldest_unacked_chunk

        self.my_socket.settimeout(None)
        fin_packet = create_packet(total_chunks + 1, 0, b'F')
        self.my_socket.sendto(fin_packet, client_address)
        print("Everything sent! Sent FIN packet.")

    def run(self):
        while True:
            self.my_socket.settimeout(None)
            try:
                incoming_data, client_addr = self.my_socket.recvfrom(2048)
                unpacked = unpack_packet(incoming_data)
                if not unpacked:
                    continue

                seq_num, ack_num, string_flag, data_len, payload_bytes = unpacked

                if string_flag == 'S':
                    print("\nGot SYN. Replying with SYN-ACK.")
                    self.my_socket.sendto(create_packet(0, seq_num + 1, b'A'), client_addr)

                elif string_flag == 'D':
                    self.my_socket.sendto(create_packet(0, seq_num, b'A'), client_addr)

                    command_string = payload_bytes.decode('utf-8')
                    if command_string.startswith("FETCH"):
                        the_url = command_string[6:].strip()
                        print(f"Client requested real file: {the_url}")

                        try:
                            my_request = urllib.request.Request(the_url, headers={'User-Agent': 'Mozilla/5.0'})
                            my_response = urllib.request.urlopen(my_request, timeout=10)
                            real_file_bytes = my_response.read()

                            print(
                                f"Successfully grabbed {len(real_file_bytes)} bytes from proxy. Starting RUDP transfer...")
                            self.serve_data(real_file_bytes, client_addr)

                        except Exception as http_error:
                            print(f"ERROR: Failed to fetch the file from {the_url}. Reason: {http_error}")

            except Exception as e:
                print(f"Error in server loop: {e}")


if __name__ == "__main__":
    server = RUDPServer()
    server.run()