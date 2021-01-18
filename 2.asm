.global  	main
.section  	.text
main:
	sw  	fp, sp, -4
	sw  	ra, sp, -8
	addi  	fp, sp, -4
	addi  	sp, sp, -28
	li  	t1, 5
	mv  	t3, t1
	sw  	t3, fp, -24
	mv  	t1, t3
	addi  	t3, t1, 5
	sw  	t3, fp, -24
	mv  	t1, t3
	addi  	t3, t1, -5
	sw  	t3, fp, -24
	mv  	t1, t3
	seqz  	t3, t1
	mv  	t1, t3
	beqz  	t1, __auto_1
__auto_0:
	lw  	t1, fp, -24
	slti  	t3, t1, 5
	mv  	t1, t3
	beqz  	t1, __auto_1
	lw  	t1, fp, -24
	mv  	t3, t1
	lw  	t1, fp, -24
	addi  	t3, t1, 1
	sw  	t3, fp, -24
	j  	__auto_0
__auto_1:
	li  	t1, 0
	mv  	t3, t1
	mv  	a0, t1
	addi  	sp, sp, 28
	lw  	fp, sp, -4
	lw  	ra, sp, -8
	ret
.section  	.data
	.align  	2

