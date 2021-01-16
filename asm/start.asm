.global     __start
.section    .text
__start:
    sw      ra, sp, -4
    addi    fp, sp, -4
    addi    sp, sp, -4
    call    main
    addi    sp, sp, 4
    lw	ra, sp, -4
    ret
.section    .data
    .align  2