import argparse
import logging
import platform
import socket
import subprocess
from enum import IntEnum


parser = argparse.ArgumentParser(
    usage="python3 mtu_finder.py [OPTIONS]", description="Path MTU Discovery"
)
parser.add_argument(
    "-H",
    "--host",
    dest="host",
    default="localhost",
    help="Specify the target network interface ip address",
)
parser.add_argument(
    "-m",
    "--mtu-max",
    dest="mtu_max",
    type=int,
    default=65535,
    help="Specify maximum MTU value to test",
)
parser.add_argument(
    "-v",
    "--verbose",
    action="store_const",
    const=True,
    dest="verbose",
    help="Enable verbose mode",
)


class MTUFinder:
    class HeaderSize(IntEnum):
        IP = 20
        ICMP = 8

    def __init__(self) -> None:
        self.system: str = platform.system()
        if self.system == "":
            raise RuntimeError(f"Couldn't determine the system OS type")
        args = parser.parse_args()
        if args.verbose is not None:
            logging.getLogger().setLevel(level=logging.INFO)

        if args.host is not None:
            try:
                ip = socket.gethostbyname(args.host)
            except socket.gaierror as err:
                logging.info(err)
                raise RuntimeError(f'Ip address: "{args.host}" is invalid')
            self.target_ip: str = ip
            logging.info(f"Target IP: {self.target_ip}")

        if args.mtu_max is not None:
            self.mtu_max: int = args.mtu_max
            if not (28 <= self.mtu_max <= 65535):
                raise RuntimeError("Max MTU size must be between 28 and 65535")

        if not self.checkAvailability():
            raise RuntimeError(f'Ip address "{self.target_ip}" is not available')
        if not self.checkICMPAvailability():
            raise RuntimeError(
                "ICMP is disabled in /proc/sys/net/ipv4/icmp_echo_ignore_all"
            )

    def checkAvailability(self) -> bool:
        result = subprocess.run(
            ["ping", "-c", "1", f"{self.target_ip}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result.returncode == 0

    def checkICMPAvailability(self) -> bool:
        if self.system != "Linux":
            return True
        result = subprocess.run(
            ["cat", "/proc/sys/net/ipv4/icmp_echo_ignore_all"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        if result.returncode != 0:
            raise RuntimeError("ICMP file is not available for check")
        return result.stdout == "0\n"

    def getPingCommand(self, packet_size) -> list[str]:
        if self.system == "Linux":
            return [
                "ping",
                "-c",
                "1",
                "-M",
                "do",
                "-s",
                f"{packet_size}",
                f"{self.target_ip}",
            ]
        elif self.system == "Windows":
            return [
                "ping",
                "-n",
                "1",
                "-M",
                "do",
                "-s",
                f"{packet_size}",
                f"{self.target_ip}",
            ]
        elif self.system == "Darwin":
            return [
                "ping",
                "-c",
                "1",
                "-D",
                "-s",
                f"{packet_size}",
                f"{self.target_ip}",
            ]
        else:
            raise RuntimeError(f'Unsupported system type: "{self.system}"')

    def tryPing(self, packet_size) -> bool:
        command: list[str] = self.getPingCommand(packet_size)
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        return result.returncode == 0

    def findMTU(self) -> int:
        lower: int = 0
        higher: int = self.mtu_max - self.HeaderSize.IP - self.HeaderSize.ICMP
        while lower < higher:
            middle: int = (lower + higher) // 2 + (lower + higher) % 2
            ping_succeeded: bool = self.tryPing(middle)
            logging.info(f"Result for {middle}: {ping_succeeded}")
            if ping_succeeded:
                lower = middle
            else:
                higher = middle - 1
        return lower + self.HeaderSize.IP + self.HeaderSize.ICMP


def main():
    try:
        mtu_finder: MTUFinder = MTUFinder()
        mtu: int = mtu_finder.findMTU()
        print(f"Resolved MTU: {mtu}")
    except RuntimeError as err:
        print(err)
    except BaseException as err:
        print("Unexpected exception:", err)


if __name__ == "__main__":
    logging.basicConfig(level=logging.CRITICAL)
    main()
