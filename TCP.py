import socket

def get_http(url: str)-> (int, dict, str):
    #Parse url
    url_site, url_page = parse_url(url)
    
    # Create a socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect to the server
    s.connect((url_site , 80))

    # Send request
    request = f"GET {url_page} HTTP/1.1\r\nHost: {url_site}\r\n\r\n"
    s.send(request.encode())

    # Receive response
    response = s.recv(4096).decode()

    # Parse response
    status_code, headers, body = parse_reponse(response)

    # Close the socket
    s.close()

    return status_code, headers, body

def parse_reponse(response: str) -> (int, dict, str):
    # Get status code
    status_code = int(response.split()[1])

    # Get headers
    headers = {}
    for line in response.split("\r\n\r\n")[0].split("\r\n")[1:]:
        header, value = line.split(": ")
        headers[header] = value

    # Get body
    body = response.split("\r\n\r\n")[1]

    return status_code, headers, body

def parse_url(url: str) -> str:
    index = url.find("/")
    return url[:index], url[index:]

if __name__ == '__main__':
    url = "gaia.cs.umass.edu/wireshark-labs/HTTP-wireshark-file1.html"
    status_code, headers, body = get_http(url)

    print(f"Status code: {status_code}")
    print("Headers:")
    for header, value in headers.items():
        print(f"\t{header} -> {value}")
    print("Body:")
    print("\t" + body.replace("\n", "\n\t"))
