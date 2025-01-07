from __future__ import annotations
from socket import timeout, socket, AF_INET, SOCK_DGRAM
from typing import Callable
import logging
import random

logger = logging.getLogger(__name__)

def __data_sum(data: bytes) -> int:
    sum = int.from_bytes(data[0:2], "big", signed=False)
    for i in range(1, len(data)//2 + 1):
        sum = (sum + int.from_bytes(data[i:i+2], "big", signed=False)) % 65535
    return sum

def create_checksum(seq_nb: int, data: bytes) -> bytes:
    # 1 bytes (seq_nb) | ? bytes (data)
    full_data = seq_nb.to_bytes(1, "big", signed=False) + data
    checksum = __data_sum(full_data) ^ ((1 << 16) - 1)
    return checksum.to_bytes(2, "big", signed=False)

def make_pkt(seq_nb: int, data: bytes, checksum: bytes) -> bytes:
    # 1 bytes (seq_nb) | 2 bytes (checksum) | ? bytes (data)
    return seq_nb.to_bytes(1, "big", signed=False) + checksum + data

def has_seq(seq_nb: int, rcvpkt: bytes) -> bool:
    return int.from_bytes(rcvpkt[0:1], "big", signed=False) == seq_nb

def isAck(rcvpkt: bytes, ack_nb: int) -> bool:
    return has_seq(ack_nb, rcvpkt) and extract(rcvpkt) == b"ACK"

def extract(rcvpkt: bytes) -> bytes:
    return rcvpkt[3:]

def corrupt(rcvpkt: bytes) -> bool:
    data = rcvpkt[0:1] + extract(rcvpkt)
    checksum = rcvpkt[1:3]
    return __data_sum(data) + int.from_bytes(checksum, "big", signed=False) != 65535


class RdtException(Exception):
    def __init__(self, src_address: tuple[str, int]):
        self.src_address = src_address
    
class Corrupted(RdtException):
    pass

class InvalidSeqNumber(RdtException):
    pass

class InvalidAckNumber(RdtException):
    pass

class RdtSocket:
    def __init__(self, buffer_size: int = 1500, corruption_rate: float = 0, packet_lost_rate: float = 0):
        self.__socket = socket(AF_INET, SOCK_DGRAM)
        self.__corruption_rate = corruption_rate
        self.__packet_lost_rate = packet_lost_rate
        self.seq_nb = 0
        self.buffer_size = buffer_size

    def udt_send(self, data: bytes, to: tuple[str, int]) -> None:
        assert len(data) <= self.buffer_size
        if random.random() < self.__packet_lost_rate:
            logger.info("Simulated packet lost.")
            return
        
        if random.random() < self.__corruption_rate:
            corruption_nb = random.randrange(0, len(data))
            data = bytearray(data)
            for _ in range(corruption_nb):
                data[random.randrange(0, len(data))] = random.randint(0, 255)
            logger.info(f"Simulated {corruption_nb} corruptions on the packet.")

        self.__socket.sendto(data, to)

    def rdt_send(self, data: bytes, to: tuple[str, int], time_out: float) -> None:
        checksum = create_checksum(self.seq_nb, data)
        logger.info(f"Computed data checksum : {checksum}")

        sndpkt = make_pkt(self.seq_nb, data, checksum)
        logger.info("Made data packet.")

        self.udt_send(sndpkt, to)
        logger.info(f"Sent new ACK packet to {to}.")

        while True:
            try:
                logger.info("Waiting for an ACK packet.")
                rcvpkt, address = self.rdt_rcv(time_out)
                logger.info(f"Received an ACK packet from {address}.")

                if isAck(rcvpkt, self.seq_nb):
                    logger.info("ACK OK.")
                    break
                else:
                    raise InvalidAckNumber(to)
            
            except (timeout, Corrupted, InvalidAckNumber):
                logger.info("Timeout, corrupted packet or invalid ACK number.")

                self.udt_send(sndpkt, to)
                logger.info(f"Resent the packet to {to}.")
        
        self.seq_nb = (self.seq_nb + 1) % 2
        logger.info(f"Changed sequence number to {self.seq_nb}.")

    def rdt_rcv(self, timeout: float | None) -> tuple[bytes, tuple[str, int]]:
        self.__socket.settimeout(timeout)

        rcvpkt, address = self.__socket.recvfrom(self.buffer_size)

        if not corrupt(rcvpkt):
            return rcvpkt, address
        else:
            raise Corrupted(address)

    def listen(self, port: int, deliver_data: Callable[[bytes], None]):
        self.__socket.bind(("", port))
        ACK = b'ACK'

        seq_nb = 0
        last_seq_nb = 1

        while True:
            try:
                logger.info(f"Waiting for a packet with sequence number {seq_nb}.")
                rcvpkt, address = self.rdt_rcv(None)
                logger.info(f"Received a packet from {address}.")
                
                if has_seq(seq_nb, rcvpkt):
                    logger.info("Packet OK.")

                    data = extract(rcvpkt)
                    logger.info("Extracted data.")

                    deliver_data(data)
                    logger.info(f"Delivered data : {data}")

                    checksum = create_checksum(seq_nb, ACK)
                    logger.info(f"Computed the ACK packet checksum : {checksum}")

                    sndpkt = make_pkt(seq_nb, ACK, checksum)
                    logger.info("Made an ACK packet.")

                    self.udt_send(sndpkt, address)
                    logger.info(f"Sent the ACK packet to {address}")

                    seq_nb, last_seq_nb = last_seq_nb, seq_nb
                    logger.info(f"Changed sequence number to {seq_nb}.")
                else:
                    raise InvalidSeqNumber(address)

            except (Corrupted, InvalidSeqNumber) as e:
                logger.info("Corrupted packet or invalid sequence number.")

                checksum = create_checksum(last_seq_nb, ACK)
                logger.info(f"Computed the new ACK packet checksum : {checksum}")

                sndpkt = make_pkt(last_seq_nb, ACK, checksum)
                logger.info("Made a new ACK packet.")

                self.udt_send(sndpkt, e.src_address)
                logger.info(f"Sent the new ACK packet to {e.src_address}")