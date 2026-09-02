
basic.out:     file format elf32-littleriscv


Disassembly of section .text:

00001000 <_start>:
	1000:	00000513          	li	a0,0
	1004:	00050663          	beqz	a0,0x1010
	1008:	00b50533          	add	a0,a0,a1
	100c:	0005a583          	lw	a1,0(a1)
	1010:	00000073          	ecall
	1014:	02b50533          	mul	a0,a0,a1
	1018:	0000202f          	amoadd.w	zero,zero,(a3)
	101c:	00000027          	flw	fa0,0(zero)
	1020:	0017d713          	srli	a4,a5,0x1
	1024:	00001234          	1234	nop
	1028:	00000000          	.word	0x00000000
	102c:	00000000          	foo.	bar
	1030:	4501          	li	a0,0
	1032:	123456          	garbage	a0,0
