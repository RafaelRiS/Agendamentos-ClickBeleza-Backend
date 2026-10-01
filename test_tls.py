import socket
import ssl

hosts = [
    "ac-acqypoi-shard-00-00.wffsjim.mongodb.net",
    "ac-acqypoi-shard-00-01.wffsjim.mongodb.net",
    "ac-acqypoi-shard-00-02.wffsjim.mongodb.net",
]

context = ssl.create_default_context()

for host in hosts:
    print(f"\nTestando: {host}")

    try:
        sock = socket.create_connection(
            (host, 27017),
            timeout=10,
        )

        tls_socket = context.wrap_socket(
            sock,
            server_hostname=host,
        )

        print("TLS OK!")
        print("Versão:", tls_socket.version())
        print("Cipher:", tls_socket.cipher())

        tls_socket.close()

    except Exception as e:
        print("ERRO:")
        print(type(e).__name__)
        print(e)
