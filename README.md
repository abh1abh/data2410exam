# DATA2410 Reliable Transport Protocol – File Transfer Application

This repository contains **`application.py`**, a reference implementation of a simple, reliable file–transfer utility that runs **on top of UDP**.<br>
It demonstrates a three‑phase protocol - _connection establishment_, _data transfer_ with a sliding window, and _connection teardown_ - referred to here as **DRTP (DATA2410 Reliable Transport Protocol)**.

---

## 1 . Prerequisites

-   Python ≥ 3.8, standard library only
-   The same port **open and unused** on both hosts (default `8088`)

Clone or download the repository, then `cd` into the project root:

```bash
$ git clone https://github.com/abh1abh/data2410exam.git
$ cd src
```

---

## 2 . Running the server (receiver)

Start **`application.py`** in **server** mode.

```bash
python3 application.py -s -i <bind_ip> -p <port> -d <seq_to_discard>
```

Example:

```bash
python3 application.py -s -p 8088
```

---

## 3 . Running the client (sender)

Start **`application.py`** in **client** mode.

```bash
python3 application.py -c -f <path_to_file> -i <server_ip> -p <port> -w <window_size>
```

Example:

```bash
python3 application.py -c -f Photo.jpg -i 10.0.1.2 -w 5
```

---

## 4 . Command‑line flags

| Short | Long form   | Argument    | Type | Description                                                       | Default | Requirement                      |
| ----- | ----------- | ----------- | ---- | ----------------------------------------------------------------- | ------- | -------------------------------- |
| `-s`  | `--server`  | —           | flag | Run as **server** (receiver)                                      | —       | Mutually exclusive with --client |
| `-c`  | `--client`  | —           | flag | Run as **client** (sender)                                        | —       | Mutually exclusive with --server |
| `-i`  | `--ip`      | IP address  | str  | _Server_: interface to bind<br>_Client_: server’s IP              | —       | Required (both)                  |
| `-p`  | `--port`    | port number | int  | UDP port used **by both peers**                                   | `8088`  | Required (both)                  |
| `-f`  | `--file`    | path        | str  | Source file to send (client only)                                 | —       | Required (client only)           |
| `-w`  | `--window`  | N ≥ 1       | int  | Sliding‑window size (client ony)                                  | `3`     | Optional (client only)           |
| `-d`  | `--discard` | seq         | int  | _Server_ test hook—drop first packet with given seq (server only) | `0`     | Optional (server only)           |

---
