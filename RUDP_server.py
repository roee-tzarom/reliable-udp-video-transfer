import socket
from RUDP_utils import create_packet, unpack_packet


class RUDPServer:
    def __init__(self, ip='127.0.0.1', port=2122):
        self.my_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Prevents "Address already in use" errors when restarting the server quickly
        self.my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.my_socket.bind((ip, port))

        self.MAX_WINDOW_LIMIT = 5
        print(f"RUDP Server is up and listening on {ip}:{port}")

    def serve_data(self, file_bytes, client_address):
        # MANUAL CHUNKING
        # Cut the big data into small pieces of 500 bytes each using a simple loop
        chunks_list = []
        current_idx = 0
        while current_idx < len(file_bytes):
            one_chunk = file_bytes[current_idx: current_idx + 500]
            chunks_list.append(one_chunk)
            current_idx = current_idx + 500

        total_chunks = len(chunks_list)
        print(f"Prepared {total_chunks} chunks for sending.")

        # AIMD CONGESTION CONTROL SETUP
        current_window_size = 1  # Start slow
        oldest_unacked_chunk = 1
        next_chunk_to_send = 1

        while oldest_unacked_chunk <= total_chunks:
            # PHASE 1: Send chunks until the window is full
            right_edge_of_window = oldest_unacked_chunk + current_window_size - 1
            if right_edge_of_window > total_chunks:
                right_edge_of_window = total_chunks

            while next_chunk_to_send <= right_edge_of_window:
                # Lists in python start at 0, so chunk 1 is index 0
                chunk_data = chunks_list[next_chunk_to_send - 1]

                # Create the DATA packet
                packet = create_packet(next_chunk_to_send, 0, b'D', chunk_data)
                self.my_socket.sendto(packet, client_address)
                print(f"Sent chunk {next_chunk_to_send}")

                next_chunk_to_send = next_chunk_to_send + 1

            # PHASE 2: Wait for the client to ACK
            self.my_socket.settimeout(1.0)  # 1 second timer for timeouts
            try:
                ack_raw, _ = self.my_socket.recvfrom(2048)
                unpacked = unpack_packet(ack_raw)

                if unpacked:
                    seq, ack_num, flag, dlen, payload = unpacked

                    if flag == 'A' and ack_num >= oldest_unacked_chunk:
                        print(f"Got ACK for chunk {ack_num}!")
                        # Move the sliding window forward
                        oldest_unacked_chunk = ack_num + 1

                        # AIMD: ADDITIVE INCREASE
                        # Network is good, let's try to send faster
                        if current_window_size < self.MAX_WINDOW_LIMIT:
                            current_window_size = current_window_size + 1
                            print(f"Window increased to {current_window_size}")

            except socket.timeout:
                # AIMD: MULTIPLICATIVE DECREASE
                # We hit a timeout! The network dropped our packet.
                print("TIMEOUT! Packet lost. Slapping brakes on the network.")
                current_window_size = current_window_size // 2  # Integer division

                if current_window_size < 1:
                    current_window_size = 1
                print(f"Window size crushed down to {current_window_size}")

                # GO-BACK-N LOGIC
                # Resend everything from the oldest unacked chunk
                next_chunk_to_send = oldest_unacked_chunk

        # OUT OF WHILE LOOP: All chunks are ACKed!
        self.my_socket.settimeout(None)

        # Send FIN packet
        fin_packet = create_packet(total_chunks + 1, 0, b'F')
        self.my_socket.sendto(fin_packet, client_address)
        print("Everything sent! Sent FIN packet.")

    def run(self):
        while True:
            # Wait forever for a client to connect and send a FETCH command
            self.my_socket.settimeout(None)
            try:
                incoming_data, client_addr = self.my_socket.recvfrom(2048)
                unpacked = unpack_packet(incoming_data)
                if not unpacked:
                    continue

                seq_num, ack_num, string_flag, data_len, payload_bytes = unpacked

                if string_flag == 'S':  # Client sent SYN
                    # Reply with SYN-ACK
                    print("Got SYN. Replying with SYN-ACK.")
                    self.my_socket.sendto(create_packet(0, seq_num + 1, b'A'), client_addr)

                elif string_flag == 'D':  # Client sent DATA (the FETCH command)
                    # Acknowledge the command
                    self.my_socket.sendto(create_packet(0, seq_num, b'A'), client_addr)

                    command_string = payload_bytes.decode('utf-8')
                    if command_string.startswith("FETCH"):
                        print(f"Client requested: {command_string}")

                        # In a real scenario for your project, this is where we would
                        # connect to the local proxy (like port 8080) to get the actual DASH video chunk.
                        # For now, let's simulate a fake video chunk of 2500 bytes (5 packets)
                        fake_video_bytes = b"X" * 2500
                        self.serve_data(fake_video_bytes, client_addr)

            except Exception as e:
                print(f"Error in server loop: {e}")


if __name__ == "__main__":
    server = RUDPServer()
    server.run()