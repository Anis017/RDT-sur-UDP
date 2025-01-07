from rdt import RdtSocket
import logging

logging.basicConfig(level=logging.INFO)

TARGET_ADDRESS = ("127.0.0.1", 666)
rdt = RdtSocket(corruption_rate=0.5, packet_lost_rate=0.5)

while True:
    data = input("Data ? ").encode("utf-8")
    rdt.rdt_send(data, TARGET_ADDRESS, 1)