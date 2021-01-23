.global  	readValue
.global  	main
.section  	.text
addi $0,$0,0
call hello
addi $0,$0,0
hello: 
ret

.section  	.data
	.align  	2

