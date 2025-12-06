#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

int main() {
    char input[100];
    char *argv[4];
    pid_t pid;

    printf("A simplified shell ... Enter exit to terminate!\n");

    while (1) {
        printf("s112213067:$ ");
        fflush(stdout);

        if (fgets(input, sizeof(input), stdin) == NULL)
            break;

        input[strcspn(input, "\n")] = '\0';

        if (strcmp(input, "exit") == 0) {
            printf("\ns112213067:$ Simplified shell terminated !\n");
            break;
        }

        int i = 0;
        argv[i] = strtok(input, " ");
        while (argv[i] != NULL && i < 3)
            argv[++i] = strtok(NULL, " ");

        if (i > 3) {
            printf("Error command! Child exit !child complete\n");
            continue;
        }

        pid = fork();
        if (pid == 0) {
            execvp(argv[0], argv);
            printf("Error command! Child exit !child complete\n");
            exit(1);
        } else {
            wait(NULL);
            printf("child complete\n");
        }
    }
    return 0;
}

