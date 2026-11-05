import os
import struct

def create_valid_mp4(filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    # ftyp box
    ftyp_data = b"isom" + struct.pack(">I", 512) + b"isomiso2avc1mp41"
    ftyp_box = struct.pack(">I", len(ftyp_data) + 8) + b"ftyp" + ftyp_data

    # mdat box (media data payload)
    mdat_payload = b"\x00" * 1024
    mdat_box = struct.pack(">I", len(mdat_payload) + 8) + b"mdat" + mdat_payload

    # moov box
    mvhd_payload = struct.pack(">I", 0) + struct.pack(">IIII", 0, 0, 1000, 1000) + struct.pack(">I", 0x00010000) + struct.pack(">H", 0x0100) + struct.pack(">H", 0) + struct.pack(">II", 0, 0) + struct.pack(">IIIIIIIII", 0x00010000,0,0,0,0x00010000,0,0,0,0x40000000) + struct.pack(">IIIIII", 0,0,0,0,0,0) + struct.pack(">I", 2)
    mvhd_box = struct.pack(">I", len(mvhd_payload) + 8) + b"mvhd" + mvhd_payload
    moov_box = struct.pack(">I", len(mvhd_box) + 8) + b"moov" + mvhd_box

    with open(filepath, "wb") as f:
        f.write(ftyp_box + mdat_box + moov_box)

if __name__ == "__main__":
    create_valid_mp4("demo/walkthrough.mp4")
    print("Created valid MP4 at demo/walkthrough.mp4")
