# Reliable UDP File Transfer Prototype

A Python client/server experiment that transfers bytes fetched from an HTTP URL over a custom UDP protocol. It demonstrates sequence numbers, cumulative acknowledgements, retransmission after timeout and a small adaptive sending window.

## How it works

- `RUDP_utils.py` packs an 11-byte network-order header: sequence number, acknowledgement number, flag and payload length (`!IIcH`).
- The client sends a SYN-style packet, then a `FETCH <url>` command.
- The server downloads the URL, splits its bytes into 500-byte chunks and sends them over UDP.
- The receiver accepts in-order chunks and acknowledges the latest contiguous sequence.
- The server grows its window on acknowledged progress (up to five packets), halves it after a one-second timeout and retransmits from the oldest unacknowledged chunk.
- Client toggles optionally simulate packet loss and latency.

## Try it locally

Run these from the repository root in three terminals:

```bash
# Terminal 1: serve the included sample payload over HTTP
python -m http.server 8080

# Terminal 2: UDP server
python RUDP_server.py

# Terminal 3: request the file
python RUDP_client.py
```

The included `video_720p.mp4` is **50 KB of generated test bytes**, created by `create_fake_video.py`; it is not a playable video. The example client prints the byte count and keeps received data in memory rather than saving or playing it. This is an educational prototype, with no checksum, authentication or production-grade congestion control.


## Packet and transfer lifecycle

`RUDP_utils.py` centralizes the binary packet format so both peers agree on the 11-byte header. A client first sends a SYN-style datagram and then a `FETCH` command containing the local HTTP URL. The server fetches the URL's bytes, slices them into 500-byte payload chunks and sends chunks within its current window. A client accepts the next expected chunk and returns a cumulative acknowledgement. After a timeout, the server halves its window and resends from the oldest unacknowledged chunk. Successful acknowledgement progress can grow the window, capped at five packets.

The application separates the source of data (HTTP) from its delivery path (custom UDP). That makes it possible to observe retransmission without changing the HTTP source. Optional client toggles add packet loss or latency for local experiments.

## Read the code in order

1. `RUDP_utils.py` defines packing and unpacking.
2. `RUDP_client.py` shows session setup, ordered receive and ACK generation.
3. `RUDP_server.py` shows HTTP fetch, chunking, window state and retries.
4. `create_fake_video.py` explains the included generated payload.

The `.mp4` filename is part of the exercise scenario, but the checked-in file is synthetic bytes. The receiver reports transfer size in memory, not playback or a saved output file. The protocol has no integrity hash, authentication, reordering buffer or general-purpose streaming player; it is a focused reliability experiment.
