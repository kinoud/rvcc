#define io(x, y) *(int*)(-1024 + x * 4 * 16 + y * 4)
int readValue() {
    int v = 0, k;
    io(0, 0) = v;
    while (1) {
        k = io(1, 0);
        io(2, 0) = k;
        if (k & 16) {
            v = v * 10 + (k & 15);
            io (0, 0) = v;
        }
    }
    return v;
}
int main() {
    io(0, 1) = 0;
    readValue();
    return 0;
}