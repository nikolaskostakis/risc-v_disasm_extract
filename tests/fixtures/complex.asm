
complex.out:     file format elf32-littleriscv



Disassembly of section .text:

00000000 <_start>:
   0:	00c5f533          	and	a0,a1,a2
   4:	00d5f533          	and	a0,a1,a3
   8:	00c58533          	add	a0,a1,a2
   c:	00359513          	slli	a0,a1,0x3
  10:	00c5a533          	slt	a0,a1,a2
  14:	fedff0ef          	jal	0 <_start>
  18:	feb514e3          	bne	a0,a1,0 <_start>
  1c:	00058503          	lb	a0,0(a1)
  20:	00a58023          	sb	a0,0(a1)
  24:	00000517          	auipc	a0,0x0
  28:	02c58533          	mul	a0,a1,a2
  2c:	02d58533          	mul	a0,a1,a3
  30:	02c5c533          	div	a0,a1,a2
  34:	02c5e533          	rem	a0,a1,a2
  38:	00b6252f          	amoadd.w	a0,a1,(a2)
  3c:	1006252f          	lr.w	a0,(a2)
  40:	00c5f553          	fadd.s	fa0,fa1,fa2
  44:	10c5f553          	fmul.s	fa0,fa1,fa2
  48:	02c5f553          	fadd.d	fa0,fa1,fa2
  4c:	4515                	li	a0,5
  4e:	8082                	ret
  50:	d945                	beqz	a0,0 <_start>
  52:	8d6d                	and	a0,a0,a1
  54:	4188                	lw	a0,0(a1)
  56:	c22e                	sw	a1,4(sp)
  58:	20c5a533          	sh1add	a0,a1,a2
  5c:	40c5f533          	andn	a0,a1,a2
  60:	60059513          	clz	a0,a1
  64:	0ac5c533          	min	a0,a1,a2
  68:	0ac59533          	clmul	a0,a1,a2
  6c:	48c5d533          	bext	a0,a1,a2
  70:	0ec5d533          	czero.eqz	a0,a1,a2
  74:	04c5f553          	fadd.h	fa0,fa1,fa2
  78:	30059573          	csrrw	a0,mstatus,a1
  7c:	0000100f          	fence.i
  80:	c0002573          	rdcycle	a0
  84:	c0302573          	csrr	a0,hpmcounter3
  88:	61c8                	flw	fa0,4(a1)
  8a:	2588                	fld	fa0,8(a1)
  8c:	9d61                	zext.b	a0,a0
  90:	08c5c533          	pack	a0,a1,a2
  94:	28c5a533          	xperm4	a0,a1,a2
  98:	06c5f553          	fadd.q	fa0,fa1,fa2
  9c:	28c5a553          	fminm.s	fa0,fa1,fa2
  a0:	00c5f553          	fadd.s	a0,a1,a2
  a4:	02e67553          	fadd.d	a0,a2,a4
  a8:	06e67553          	fadd.q	a0,a2,a4
  ac:	04c5f553          	fadd.h	a0,a1,a2
  b0:	4485f553          	fcvt.bf16.s	fa0,fa1



Disassembly of section .text:

00000000 <_start>:
   0:	0105f557          	vsetvli	a0,a1,e32,m1,tu,mu
   4:	022180d7          	vadd.vv	v1,v2,v3
   8:	02056087          	vle32.v	v1,(a0)
   c:	020560a7          	vse32.v	v1,(a0)
  10:	9621a0d7          	vmul.vv	v1,v2,v3
  14:	0c8072d7          	vsetvli	t0,zero,e16,m1,ta,ma
  18:	4a2690d7          	vfwcvtbf16.f.f.v	v1,v2
  1c:	4a2e90d7          	vfncvtbf16.f.f.w	v1,v2
  20:	ee3110d7          	vfwmaccbf16.vv	v1,v2,v3



Disassembly of section .text:

00000000 <_start>:
   0:	b842                	cm.push	{ra},-16
   2:	a016                	cm.jt	5
   4:	abcdef01          	reserved0	a0,a1
