#ifndef __TASK_H__
#define __TASK_H__

#include <stdbool.h>
#include <stdint-gcc.h>
#include <stddef.h>
#include <rbtree.h>
#include <mem_layout.h>

#define MAX_TASK	((SVC_STACK_BASE-SYS_STACK_BASE)/(TASK_STACK_GAP))
#define MAX_USR_TASK	5 /* max user task num is 5 */

enum {
	USR_TASK0=0,
	USR_TASK1,
	USR_TASK2,
	USR_TASK3,
	USR_TASK4
};

enum {
	TASK_RUNNING,
	TASK_WAITING,
	TASK_STOP_RUNNING,
	TASK_STOP
};

struct list_head {
	struct list_head *prev, *next;
};

typedef int (*task_entry)(void);

struct sched_entity {
	uint64_t vruntime;
	/*uint64_t jiffies_consumed;*/
	uint64_t ticks_consumed;
	struct rb_node run_node;
	uint32_t priority;
};

struct cfs_rq {
	struct sched_entity *curr, *next, *last;
	struct rb_root root;
	struct rb_node *rb_leftmost;
	uint32_t priority_sum;
};
/* do not change the order */
struct task_context_struct {
	uint32_t pc;
	uint32_t lr;
	uint32_t sp;
	uint32_t r[13];
	uint32_t spsr;
#ifdef USE_MMU
	uint32_t ttb; /* translation base address */
#endif
};

typedef enum {
	CFS_TASK = 0,
	RT_TASK,
	ONESHOT_TASK,
}TASKTYPE;

struct task_struct {
	struct task_context_struct ct;
	/*struct task_context_struct ct;*/
	task_entry entry;
	void *arg;
	char name[32];
	struct sched_entity se;
	struct list_head task;
	struct task_struct *yield_task;
	struct list_head waitlist;
	TASKTYPE type; 
	uint32_t missed_cnt;
	uint32_t state;
};

void init_cpuidle_task(void);
void init_task(void);
void init_jiffies(void);
void init_task(void);
void create_all_task(void);
void forkyi(struct task_struct *pbt, struct task_struct *pt);
#ifdef USE_MMU
struct task_struct *do_forkyi(char *name, task_entry fn, int idx, unsigned int *ppd);
#else
struct task_struct *do_forkyi(char *name, task_entry fn, int idx, TASKTYPE type);
#endif
void switch_context(struct task_struct *prev, struct task_struct *next);
void schedule(void);
void dequeue_se_to_exit(struct cfs_rq *rq, struct sched_entity *se);
void enqueue_se_to_runq(struct cfs_rq *rq, struct sched_entity *se, bool update);
void dequeue_se_to_waitq(struct cfs_rq *rq, struct sched_entity *se, bool update);
void drop_usrtask();
#ifdef USE_MMU
void init_shell(unsigned int *ppd);
void init_idletask(unsigned int *ppd);
#else
void init_shell();
void init_idletask();
#endif
void update_se(uint32_t elasped);
void set_priority(struct task_struct *pt, uint32_t pri);
void put_to_sleep(char *dur, int idx);
void yield();
void create_rt_task(char *name, task_entry handler, int dur);


void func1(void);
void func2(void);
static inline struct task_struct *to_task_from_listhead(struct list_head *t)
{       
	/*return container_of(t, struct task_struct, task);*/
	return ((struct task_struct *)((unsigned int)t-offsetof(struct task_struct, task)));
}

static inline struct task_struct *to_task_from_se(struct sched_entity *s)
{       
	/*return container_of(t, struct task_struct, task);*/
	return ((struct task_struct *)((unsigned int)s-offsetof(struct task_struct, se)));
}
#endif
