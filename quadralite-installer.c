#include <stdio.h>
#include <stdlib.h>

int main(void) {
    printf("Quadra Lite installer\n");
    printf("Downloading the latest installer...\n");
    if (system("curl -fsSL https://raw.githubusercontent.com/Schlabbadabadoo/Quadra-Lite/main/install.sh -o /tmp/quadralite-install.sh") != 0) {
        fprintf(stderr, "Download failed. Check your internet connection.\n");
        return 1;
    }
    system("chmod +x /tmp/quadralite-install.sh");
    return system("/tmp/quadralite-install.sh");
}
