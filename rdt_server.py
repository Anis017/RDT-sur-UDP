from rdt import RdtSocket
import logging

logging.basicConfig(level=logging.INFO)

PORT = 666
rdt = RdtSocket(corruption_rate=0.5, packet_lost_rate=0.5)

def deliver_data(data):
    print(str(data, "utf-8"))

print(f"Listening to port {PORT}")
rdt.listen(PORT, deliver_data)