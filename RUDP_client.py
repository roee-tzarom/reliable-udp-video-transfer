import socket
import random
import time
from RUDP_utils import create_packet, unpack_packet


class RUDPClient:
    def __init__(self):
        self.my_rudp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Timeout of 5 seconds just like the original code
        self.my_rudp_socket.settimeout(5.0)

        # --- THE SIMULATION TOGGLES ---
        # Keep these True to prove the Go-Back-N actually works
        self.I_WANT_TO_SIMULATE_PACKET_LOSS = True
        self.I_WANT_TO_SIMULATE_LATENCY = True

        self.destination_tuple = None

    def connect(self, server_ip, server_port):
        self.destination_tuple = (server_ip, server_port)
        print("Sending SYN packet to start connection...")

        # Seq=100, Ack=0, Flag='S' (SYN)
        syn_packet = create_packet(100, 0, b'S')
        self.my_rudp_socket.sendto(syn_packet, self.destination_tuple)

        # Wait for SYN-ACK from server
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
        # Shira will call this function in her DASH loop!
        my_command = f"FETCH {url_to_download}".encode('utf-8')

        # Send the FETCH command
        command_packet = create_packet(101, 0, b'D', my_command)
        self.my_rudp_socket.sendto(command_packet, self.destination_tuple)

        try:
            # Wait for server to ACK the command
            self.my_rudp_socket.recvfrom(2048)
            print(f"Server acknowledged FETCH for {url_to_download}. Waiting for data...")
        except socket.timeout:
            print("Server didn't ACK the command.")
            return b''

        # --- The Go-Back-N Receive Loop ---
        all_file_bytes = b''
        the_chunk_i_am_expecting = 1

        while True:
            try:
                incoming_packet, _ = self.my_rudp_socket.recvfrom(2048)
                unpacked = unpack_packet(incoming_packet)
                if not unpacked:
                    continue

                inc_seq, inc_ack, string_flag, inc_len, inc_payload = unpacked

                if string_flag == 'D':  # If it is a DATA chunk
                    # 1. Latency Simulation
                    if self.I_WANT_TO_SIMULATE_LATENCY:
                        fake_delay = random.uniform(0.1, 0.4)
                        time.sleep(fake_delay)

                    # 2. Packet Loss Simulation
                    if self.I_WANT_TO_SIMULATE_PACKET_LOSS:
                        random_number = random.random()
                        if random_number < 0.3:  # 30% chance to drop
                            print(f"SIMULATING PACKET LOSS! Dropping Chunk {inc_seq}")
                            continue  # Skip the rest of the loop, no ACK sent

                    # 3. Cumulative ACK Logic (Go-Back-N)
                    if inc_seq == the_chunk_i_am_expecting:
                        # Good! It's in order.
                        all_file_bytes = all_file_bytes + inc_payload
                        the_chunk_i_am_expecting = the_chunk_i_am_expecting + 1

                        # Tell the server "I got this specific sequence number"
                        my_ack_packet = create_packet(0, inc_seq, b'A')
                        self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)
                    else:
                        # Out of order! Send ACK for the last good chunk we have.
                        last_good_chunk = the_chunk_i_am_expecting - 1
                        print(
                            f"Got chunk {inc_seq} but wanted {the_chunk_i_am_expecting}. Sending old ACK for {last_good_chunk}.")
                        my_ack_packet = create_packet(0, last_good_chunk, b'A')
                        self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)

                elif string_flag == 'F':  # If it is a FIN packet
                    print("Server sent FIN. This specific chunk transfer is done.")
                    # Acknowledge the FIN
                    my_ack_packet = create_packet(0, inc_seq, b'A')
                    self.my_rudp_socket.sendto(my_ack_packet, self.destination_tuple)
                    break  # Exit the while loop

            except socket.timeout:
                print("The socket timed out while receiving data.")
                break

        return all_file_bytes

    def close(self):
        self.my_rudp_socket.close()