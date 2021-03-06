#include <vm_pool.h>
#include <page_table.h>

#define PAGE_SIZE	(4 * 1024)

void init_vmpool(struct vmpool *pvmpool,
		struct pagetable *_pagetable,
   	    	unsigned int _base_address,
	    	unsigned int _size)
{
	pvmpool->ppagetable = _pagetable;
	pvmpool->base_address = _base_address;
	pvmpool->size = _size;

#if 0
	pvmpool->ppagetable->register_vmpool(this);
#endif

	/* alloc a frame for region descriptor
	 * to do this, generate a page fault 
	 * at the base address
	 */
	pvmpool->pcur_region = (struct region_desc *)(pvmpool->base_address);
	/* generate a page fault 
	 * set the bit[0] with 1 as it is allocated 
	 * for region descriptor
	 */
	pvmpool->pcur_region->startAddr = pvmpool->base_address;
	pvmpool->pcur_region->size = PAGE_SIZE;
	pvmpool->pcur_region->prev = 0;
	pvmpool->pcur_region->next = 0;
	pvmpool->region_page_total = PAGE_SIZE;
}

/* lazy allocator */
unsigned int allocate(struct vmpool *pvmpool, unsigned int _size)
{
	unsigned int pgnum;

	/* allocate multiple of page, internal fragmentation allowed */
	pgnum = (int)(_size/PAGE_SIZE) + (_size%PAGE_SIZE ? 1 : 0);

	if(!pvmpool->pcur_region) {
		pvmpool->pcur_region = (struct region_desc *)(pvmpool->base_address);
		while(pvmpool->pcur_region->next) {
			pvmpool->pcur_region = pvmpool->pcur_region->next; 
		}
	}

	pvmpool->pcur_region->next = pvmpool->pcur_region + 1;
	pvmpool->pcur_region->next->prev = pvmpool->pcur_region;
	pvmpool->pcur_region = pvmpool->pcur_region->next;
	pvmpool->pcur_region->startAddr = pvmpool->base_address + pvmpool->region_page_total;
	pvmpool->pcur_region->size = _size;
	pvmpool->pcur_region->next = 0;

	/* always allocate multiples of page size */
	pvmpool->region_page_total += (PAGE_SIZE * pgnum);

	return pvmpool->pcur_region->startAddr;
}

void release(struct vmpool *pvmpool, unsigned int _start_address)
{
	int i;
	unsigned int region_size;
	unsigned int pgnum;
	struct region_desc *pcur = (struct region_desc *)(pvmpool->base_address);

	while(pcur) {
		if(pcur->startAddr == _start_address) {
			pcur->prev->next = pcur->next;
			if(pcur->next) 
				pcur->next->prev = pcur->prev;
			region_size = pcur->size;
			pgnum = (int)(region_size/PAGE_SIZE) + (region_size%PAGE_SIZE ? 1 : 0);
			for(i=0 ; i<pgnum ; i++) {
				free_page((unsigned int)(_start_address+(PAGE_SIZE*i)));
			}
			if(i == pgnum) {
				/* flushing TLB and reload page table */
				load_pagetable(pvmpool->ppagetable);
				pvmpool->region_page_total -= (pgnum * PAGE_SIZE);
			}
			break;
		}
		pcur = pcur->next;
	}

	if(pvmpool->pcur_region->startAddr == _start_address) {
		pvmpool->pcur_region = (struct region_desc *)(pvmpool->base_address);
		while(pvmpool->pcur_region->next) {
			pvmpool->pcur_region = pvmpool->pcur_region->next; 
		}
	}
}

int is_legitimate(struct vmpool *pvmpool, unsigned int _address)
{
	struct region_desc *pcur = (struct region_desc *)(pvmpool->base_address);

	if(_address == pvmpool->base_address) return 1;

	pcur = pcur->next;
	while(pcur) {
		if(_address >= pcur->startAddr && _address < pcur->startAddr + pcur->size) return 1;
		else pcur = pcur->next;
	}

	return 0;
}
