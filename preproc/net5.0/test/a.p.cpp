# 1 "a.c"

int readValue() {
    int v = 0, k;
    *(int*)(-1024 + 0 * 4 * 16 +  0 * 4) = v;
    while (1) {
        k = *(int*)(-1024 + 1 * 4 * 16 +  0 * 4);
        *(int*)(-1024 + 2 * 4 * 16 +  0 * 4) = k;
        if (k & 16) {
            v = v * 10 + (k & 15);
            *(int*)(-1024 + 0 * 4 * 16 +  0 * 4) = v;
        }
    }
    return v;
}
int main() {
    *(int*)(-1024 + 0 * 4 * 16 +  1 * 4) = 0;
    readValue();
    return 0;
}