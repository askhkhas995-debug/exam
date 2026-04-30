#include <unistd.h>

void print_nth_char(char *str, int n);

int main(void)
{
    print_nth_char("ABCDEF", 2);
    print_nth_char("Hello", 2);
    print_nth_char("ABC", 1);
    return (0);
}
