.global  	main
.section  	.text
main:
	sw  	fp, sp, -4
	sw  	ra, sp, -8
	addi  	fp, sp, -4
	addi  	sp, sp, -16
	li  	t1, 1
	mv  	t3, t1
	li  	t1, 0
	mv  	t3, t1
	mv  	a0, t1
	addi  	sp, sp, 16
	lw  	fp, sp, -4
	lw  	ra, sp, -8
	ret
.section  	.data
	.align  	2

