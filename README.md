# Reliable UDP Media Transfer Prototype

A Python client and server that fetch bytes from a local HTTP endpoint and move them over a custom UDP protocol. The project makes sequence tracking, cumulative acknowledgements, retransmission and window adjustment visible in a compact implementation.

## Transfer lifecycle

1. The client sends a SYN-style datagram to the UDP server.
2. It requests an HTTP URL with a `FETCH` command.
3. The server downloads the source bytes, divides them into 500-byte chunks and sends a window of datagrams.
4. The client accepts the next expected chunk and acknowledges the latest contiguous sequence.
5. The server grows its window as ACKs advance, up to five packets; after a timeout it halves the window and retransmits from the oldest outstanding chunk.

`RUDP_utils.py` defines the common 11-byte network-order header: sequence number, acknowledgement number, one-byte flag and payload length (`!IIcH`). The client can optionally simulate packet loss and latency to expose the recovery path.

## Run locally

Use Python 3 and three terminals from the repository root:

```bash
# Serve the included payload over HTTP
python -m http.server 8080

# Start the UDP receiver's peer
python RUDP_server.py

# Request the payload
python RUDP_client.py
```

The client requests `http://127.0.0.1:8080/video_720p.mp4` from the server and reports the number of bytes received. It keeps the result in memory; it does not save or play a video.

## Important note about the sample file

`video_720p.mp4` is approximately 50 KB of generated test bytes produced by `create_fake_video.py`. The extension supports the transfer scenario, but the file is not a playable video. This keeps the protocol demonstration small and repeatable.

## Repository map

| File | Role |
| --- | --- |
| `RUDP_utils.py` | Packet encoding and decoding |
| `RUDP_server.py` | HTTP fetch, chunking, send window and retries |
| `RUDP_client.py` | Session setup, ordered receive and ACKs |
| `create_fake_video.py` | Generates the synthetic payload |

This prototype focuses on delivery mechanics. It has no authentication, file-integrity hash, out-of-order receive buffer or video playback pipeline.
