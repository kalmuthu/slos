# Copyright (c) 2012-2013, The Linux Foundation. All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 and
# only version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import sys
import re
import os
import struct
import datetime
import array
import string
import bisect
import traceback
import gzip
import functools
import platform
import subprocess as subp
from optparse import OptionParser
from optparse import OptionGroup
from struct import unpack
from ctypes import *
from tempfile import *
from print_out import *
from qdss import *
from mm import *

HARDWARE_ID_IDX = 0
MEMORY_START_IDX = 1
PHYS_OFFSET_IDX = 2
WATCHDOG_BARK_OFFSET_IDX = 3
IMEM_START_IDX = 4
CPU_TYPE = 5
IMEM_FILENAME = 6
VERSION_COMPARE = 7

smem_offsets = [
                0, # 8960/9x15 family and earlier
                0x0FA00000, # 8974
                0x00100000,
                0x0D900000, # 8610
               ]

hw_ids = [
    (8660, 0x40000000, 0x40200000, 0x2a05f658, 0x2a05f000, "SCORPION", "IMEM_C.BIN", None),
    (8960, 0x80000000, 0x80200000, 0x2a03f658, 0x2a03f000, "KRAIT",    "IMEM_C.BIN", None),
    (8064, 0x80000000, 0x80200000, 0x2a03f658, 0x2a03f000, "KRAIT",    "IMEM_C.BIN", None),
    (9615, 0x40000000, 0x40800000, 0x0,        0x0,        "CORTEXA5", None,         None),
    (8974, 0x0,        0x0,        0xfc42b658, 0xfc428000, "KRAIT",    "MSGRAM.BIN", 1),
    (8974, 0x0,        0x0,        0xfe805658, 0xfe800000, "KRAIT",    "OCIMEM.BIN", 2),
    (9625, 0x0,        0x00200000, 0xfc42b658, 0xfc428000, "CORTEXA5", "MSGRAM.BIN", 1),
    (9625, 0x0,        0x00200000, 0xfe805658, 0xfe800000, "CORTEXA5", "OCIMEM.BIN", 2),
    (8625, 0x0,        0x00200000, 0x0,        0x0,        "SCORPION",  None,        None),
    (8626, 0x0,        0x00000000, 0xfe805658, 0xfe800000, "CORTEXA7", "OCIMEM.BIN", None),
    (8226, 0x0,        0x00000000, 0xfe805658, 0xfe800000, "CORTEXA7", "OCIMEM.BIN", None),
    (8610, 0x0,        0x00000000, 0xfe805658, 0xfe800000, "CORTEXA7", "OCIMEM.BIN", None),
    (8926, 0x0,        0x00000000, 0xfe805658, 0xfe800000, "CORTEXA7", "OCIMEM.BIN", None),
    (8026, 0x0,        0x00000000, 0xfe805658, 0xfe800000, "CORTEXA7", "OCIMEM.BIN", None),
    ]

MSM_CPU_UNKNOWN = 0
MSM_CPU_7X01 = -1
MSM_CPU_7X25 = -1
MSM_CPU_7X27 = -1
MSM_CPU_8X50 = -1
MSM_CPU_8X50A = -1
MSM_CPU_7X30 = -1
MSM_CPU_8X55 = -1
MSM_CPU_8X60 = 8660
MSM_CPU_8960 = 8960
MSM_CPU_8960AB = 8960
MSM_CPU_7X27A = 8625
FSM_CPU_9XXX = -1
MSM_CPU_7X25A = 8625
MSM_CPU_7X25AA = 8625
MSM_CPU_7X25AB = 8625
MSM_CPU_8064 = 8064
MSM_CPU_8064AB = 8064
MSM_CPU_8930 = 8960
MSM_CPU_8930AA = 8960
MSM_CPU_8930AB = 8960
MSM_CPU_7X27AA = -1
MSM_CPU_9615 = 9615
MSM_CPU_8974 = 8974
MSM_CPU_8627 = 8960
MSM_CPU_8625 = 9615
MSM_CPU_9625 = 9625
MSM_CPU_8626 = 8626
MSM_CPU_8226 = 8226
MSM_CPU_8610 = 8610
MSM_CPU_8110 = 8110
MSM_CPU_8210 = 8210
MSM_CPU_8810 = 8810
MSM_CPU_8926 = 8926
MSM_CPU_8026 = 8026

    # id, cpu, cpuname
cpu_of_id = [
    # 7x01 IDs
    (1,  MSM_CPU_7X01, "MSM_CPU_7X01"),
    (16, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (17, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (18, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (19, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (23, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (25, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (26, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (32, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (33, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (34, MSM_CPU_7X01, "MSM_CPU_7X01"),
    (35, MSM_CPU_7X01, "MSM_CPU_7X01"),

    # 7x25 IDs
    (20, MSM_CPU_7X25, "MSM_CPU_7X25"),
    (21, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7225
    (24, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7525
    (27, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7625
    (39, MSM_CPU_7X25, "MSM_CPU_7X25"),
    (40, MSM_CPU_7X25, "MSM_CPU_7X25"),
    (41, MSM_CPU_7X25, "MSM_CPU_7X25"),
    (42, MSM_CPU_7X25, "MSM_CPU_7X25"),
    (62, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7625-1
    (63, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7225-1
    (66, MSM_CPU_7X25, "MSM_CPU_7X25"), # 7225-2


    # 7x27 IDs
    (43, MSM_CPU_7X27, "MSM_CPU_7X27"),
    (44, MSM_CPU_7X27, "MSM_CPU_7X27"),
    (61, MSM_CPU_7X27, "MSM_CPU_7X27"),
    (67, MSM_CPU_7X27, "MSM_CPU_7X27"), # 7227-1
    (68, MSM_CPU_7X27, "MSM_CPU_7X27"), # 7627-1
    (69, MSM_CPU_7X27, "MSM_CPU_7X27"), # 7627-2


    # 8x50 IDs
    (30, MSM_CPU_8X50, "MSM_CPU_8X50"),
    (36, MSM_CPU_8X50, "MSM_CPU_8X50"),
    (37, MSM_CPU_8X50, "MSM_CPU_8X50"),
    (38, MSM_CPU_8X50, "MSM_CPU_8X50"),

    # 7x30 IDs
    (59, MSM_CPU_7X30, "MSM_CPU_7X30"),
    (60, MSM_CPU_7X30, "MSM_CPU_7X30"),

    # 8x55 IDs
    (74, MSM_CPU_8X55, "MSM_CPU_8X55"),
    (75, MSM_CPU_8X55, "MSM_CPU_8X55"),
    (85, MSM_CPU_8X55, "MSM_CPU_8X55"),

    # 8x60 IDs
    (70, MSM_CPU_8X60, "MSM_CPU_8X60"),
    (71, MSM_CPU_8X60, "MSM_CPU_8X60"),
    (86, MSM_CPU_8X60, "MSM_CPU_8X60"),

    # 8960 IDs
    (87, MSM_CPU_8960, "MSM_CPU_8960"),

    # 7x25A IDs
    (88, MSM_CPU_7X25A, "MSM_CPU_7X25A"),
    (89, MSM_CPU_7X25A, "MSM_CPU_7X25A"),
    (96, MSM_CPU_7X25A, "MSM_CPU_7X25A"),

    # 7x27A IDs
    (90, MSM_CPU_7X27A, "MSM_CPU_7X27A"),
    (91, MSM_CPU_7X27A, "MSM_CPU_7X27A"),
    (92, MSM_CPU_7X27A, "MSM_CPU_7X27A"),
    (97, MSM_CPU_7X27A, "MSM_CPU_7X27A"),

    # FSM9xxx ID
    (94, FSM_CPU_9XXX, "FSM_CPU_9XXX"),
    (95, FSM_CPU_9XXX, "FSM_CPU_9XXX"),

    #  7x25AA ID
    (98, MSM_CPU_7X25AA, "MSM_CPU_7X25AA"),
    (99, MSM_CPU_7X25AA, "MSM_CPU_7X25AA"),
    (100, MSM_CPU_7X25AA, "MSM_CPU_7X25AA"),

    #  7x27AA ID
    (101, MSM_CPU_7X27AA, "MSM_CPU_7X27AA"),
    (102, MSM_CPU_7X27AA, "MSM_CPU_7X27AA"),
    (103, MSM_CPU_7X27AA, "MSM_CPU_7X27AA"),

    # 9x15 ID
    (104, MSM_CPU_9615, "MSM_CPU_9615"),
    (105, MSM_CPU_9615, "MSM_CPU_9615"),
    (106, MSM_CPU_9615, "MSM_CPU_9615"),
    (107, MSM_CPU_9615, "MSM_CPU_9615"),

    # 8064 IDs
    (109, MSM_CPU_8064, "MSM_CPU_8064"),
    (130, MSM_CPU_8064, "MSM_CPU_8064"),

    # 8930 IDs
    (116, MSM_CPU_8930, "MSM_CPU_8930"),
    (117, MSM_CPU_8930, "MSM_CPU_8930"),
    (118, MSM_CPU_8930, "MSM_CPU_8930"),
    (119, MSM_CPU_8930, "MSM_CPU_8930"),

    # 8627 IDs
    (120, MSM_CPU_8627, "MSM_CPU_8627"),
    (121, MSM_CPU_8627, "MSM_CPU_8627"),

    # 8660A ID
    (122, MSM_CPU_8960, "MSM_CPU_8960"),

    # 8260A ID
    (123, MSM_CPU_8960, "8260A"),

    # 8060A ID
    (124, MSM_CPU_8960, "8060A"),

    # Copper IDs
    (126, MSM_CPU_8974, "MSM_CPU_8974"),

    # 8625 IDs
    (127, MSM_CPU_8625, "MSM_CPU_8625"),
    (128, MSM_CPU_8625, "MSM_CPU_8625"),
    (129, MSM_CPU_8625, "MSM_CPU_8625"),

    # 8064 MPQ ID */
    (130, MSM_CPU_8064, "MSM_CPU_8064"),

    # 7x25AB IDs
    (131, MSM_CPU_7X25AB, "MSM_CPU_7X25AB"),
    (132, MSM_CPU_7X25AB, "MSM_CPU_7X25AB"),
    (133, MSM_CPU_7X25AB, "MSM_CPU_7X25AB"),
    (135, MSM_CPU_7X25AB, "MSM_CPU_7X25AB"),

    # 9625 IDs
    (134, MSM_CPU_9625, "MSM_CPU_9625"),
    (148, MSM_CPU_9625, "MSM_CPU_9625"),
    (149, MSM_CPU_9625, "MSM_CPU_9625"),
    (150, MSM_CPU_9625, "MSM_CPU_9625"),
    (151, MSM_CPU_9625, "MSM_CPU_9625"),
    (152, MSM_CPU_9625, "MSM_CPU_9625"),
    (173, MSM_CPU_9625, "MSM_CPU_9625"),
    (174, MSM_CPU_9625, "MSM_CPU_9625"),
    (175, MSM_CPU_9625, "MSM_CPU_9625"),

    # 8960AB IDs
    (138, MSM_CPU_8960AB, "MSM_CPU_8960AB"),
    (139, MSM_CPU_8960AB, "MSM_CPU_8960AB"),
    (140, MSM_CPU_8960AB, "MSM_CPU_8960AB"),
    (141, MSM_CPU_8960AB, "MSM_CPU_8960AB"),

    # 8930AA IDs
    (142, MSM_CPU_8930AA, "MSM_CPU_8930AA"),
    (143, MSM_CPU_8930AA, "MSM_CPU_8930AA"),
    (144, MSM_CPU_8930AA, "MSM_CPU_8930AA"),

    # 8226 IDx
    (145, MSM_CPU_8626, "MSM_CPU_8626"),

    # 8610 IDx
    (147, MSM_CPU_8610, "MSM_CPU_8610"),
    (161, MSM_CPU_8610, "MSM_CPU_8610"),
    (162, MSM_CPU_8610, "MSM_CPU_8610"),
    (163, MSM_CPU_8610, "MSM_CPU_8610"),
    (164, MSM_CPU_8610, "MSM_CPU_8610"),
    (165, MSM_CPU_8610, "MSM_CPU_8610"),
    (166, MSM_CPU_8610, "MSM_CPU_8610"),

    # 8064AB IDs
    (153, MSM_CPU_8064AB, "MSM_CPU_8064AB"),

    # 8930AB IDs
    (154, MSM_CPU_8930AB, "MSM_CPU_8930AB"),
    (155, MSM_CPU_8930AB, "MSM_CPU_8930AB"),
    (156, MSM_CPU_8930AB, "MSM_CPU_8930AB"),
    (157, MSM_CPU_8930AB, "MSM_CPU_8930AB"),

    (158, MSM_CPU_8226, "MSM_CPU_8226"),

    (160, MSM_CPU_8930AA, "MSM_CPU_8930AA"),

    (200, MSM_CPU_8926, "MSM_CPU_8926"),

    (199, MSM_CPU_8026, "MSM_CPU_8026"),
    # Uninitialized IDs are not known to run Linux.
    # MSM_CPU_UNKNOWN is set to 0 to ensure these IDs are
    # considered as unknown CPU.
]

socinfo_v1 = functools.reduce(lambda x, y: x + y, [
    "I", # format
    "I", # id
    "I", # version
])

launch_config_str="OS=\nID=T32_1000002\nTMP=C:\\TEMP\nSYS=C:\\T32\nHELP=C:\\T32\\pdf\n\nPBI=SIM\nSCREEN=\nFONT=SMALL\nHEADER=Trace32-ScorpionSimulator\nPRINTER=WINDOWS"


offsets_common_3_0= [
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct task_struct *)0x0)", "pid", 0, 0),
    ("((struct task_struct *)0x0)", "tasks", 0, 0),
    ("((struct task_struct *)0x0)", "stack", 0, 0),
    ("((struct task_struct *)0x0)", "thread_group", 0, 0),
    ("((struct task_struct *)0x0)", "state", 0, 0),
    ("((struct task_struct *)0x0)", "exit_state", 0, 0),
    ("((struct work_struct *)0x0)", "func", 0, 0),
    ("((struct work_struct *)0x0)", "entry", 0, 0),
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct delayed_work *)0x0)", "timer", 0, 0),
    ("((struct timer_list *)0x0)", "expires", 0, 0),
    ("((struct global_cwq *)0x0)", "worklist", 0, 0),
    ("sizeof(__log_buf)","",0, 1),
    ("sizeof(kernel_config_data)","",0, 1),
    ]

offsets_common_3_4= [
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct task_struct *)0x0)", "pid", 0, 0),
    ("((struct task_struct *)0x0)", "tasks", 0, 0),
    ("((struct task_struct *)0x0)", "stack", 0, 0),
    ("((struct task_struct *)0x0)", "thread_group", 0, 0),
    ("((struct task_struct *)0x0)", "state", 0, 0),
    ("((struct task_struct *)0x0)", "exit_state", 0, 0),
    ("((struct work_struct *)0x0)", "func", 0, 0),
    ("((struct work_struct *)0x0)", "entry", 0, 0),
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct delayed_work *)0x0)", "timer", 0, 0),
    ("((struct timer_list *)0x0)", "expires", 0, 0),
    ("sizeof(__log_buf)","",0, 1),
    ("sizeof(kernel_config_data)","",0, 1),
    ]

offsets_common_3_7= [
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct task_struct *)0x0)", "pid", 0, 0),
    ("((struct task_struct *)0x0)", "tasks", 0, 0),
    ("((struct task_struct *)0x0)", "stack", 0, 0),
    ("((struct task_struct *)0x0)", "thread_group", 0, 0),
    ("((struct task_struct *)0x0)", "state", 0, 0),
    ("((struct task_struct *)0x0)", "exit_state", 0, 0),
    ("((struct work_struct *)0x0)", "func", 0, 0),
    ("((struct work_struct *)0x0)", "entry", 0, 0),
    ("((struct task_struct *)0x0)", "comm", 0, 0),
    ("((struct delayed_work *)0x0)", "timer", 0, 0),
    ("((struct timer_list *)0x0)", "expires", 0, 0),
    ("sizeof(__log_buf)","",0, 1),
    ("sizeof(kernel_config_data)","",0, 1),
    ]



offsets_early = [
    ("((struct smem_shared *)0x0)", "heap_toc", 0, 0),
    ("sizeof(struct smem_heap_entry)", "", 0, 1),
    ("((struct smem_heap_entry *)0x0)", "offset", 0, 0),
]

generic_mem_offsets = [
        ("((struct page *)0x0)", "flags", 0, 0),
        ("((struct pglist_data *)0x0)", "node_zones", 0, 0),
        ("sizeof(struct zone)","",0, 1),
        ("sizeof(struct page)","",0, 1),
        ("((struct zone *)0x0)","name",0, 0),
        ("sizeof(page_address_htable[0])","",0,1),
        ("((struct page_address_map *)0x0)","page",0, 0),
        ("((struct page_address_map *)0x0)","virtual",0, 0),
        ("((struct page *)0x0)","_mapcount", 0, 0),
]

sparsemem_offsets = [
        ("((struct mem_section *)0x0)","section_mem_map",0, 0),
        ("sizeof(struct mem_section)","",0, 1),
]


# The smem code is very stable and unlikely to go away or be changed.
# Rather than go through the hassel of parsing the id through gdb,
# just hard code it

SMEM_HW_SW_BUILD_ID=0x89
BUILD_ID_LENGTH=32

first_mem_file_names = [ "EBICS0.BIN", "EBI1.BIN", "DDRCS0.BIN", "ebi1_cs0.bin" ]
extra_mem_file_names = [ "EBI1CS1.BIN", "DDRCS1.BIN", "ebi1_cs1.bin" ]

def get_system_type() :
    plat = platform.system()

    if plat == 'Windows' :
       return 'Windows'
    if re.search('CYGWIN',plat) is not None :
       # On certain installs, the default windows shell
       # runs cygwin. Treat cygwin as windows for this
       # purpose
       return 'Windows'
    if plat == 'Linux' :
       return 'Linux'

    if plat == 'Darwin' :
       return 'Darwin'

    print_out_str ("[!!!] This is a target I don't recognize!")
    print_out_str ("[!!!] Some features may not work as expected!")
    print_out_str ("[!!!] Assuming Linux...")


class RamDump() :
    def __init__ (self, vmlinux_path, nm_path, gdb_path, ebi, file_path, phys_offset, outdir, hw_id = None, hw_version = None) :
        self.ebi_files = []
        self.phys_offset = None
        self.tz_start = 0
        self.ebi_start = 0
        self.cpu_type = None
        self.hw_id = hw_id
        self.hw_version = hw_version
        self.offset_table = []
        self.vmlinux = vmlinux_path
        self.nm_path = nm_path
        self.gdb_path = gdb_path
        self.outdir = outdir
        self.setup_offset_table(offsets_early)
        self.imem_fname = None
        if ebi is not None:
            # TODO sanity check to make sure the memory regions don't overlap
            for file_path,start,end in ebi :
                fd = open(file_path, "rb")
                if not fd :
                    print_out_str ("Could not open {0}. Will not be part of dump".format(file_path))
                    continue
                self.ebi_files.append((fd,start,end,file_path))
        else :
            if not self.auto_parse(file_path) :
                return None
        if self.ebi_start == 0 :
            self.ebi_start = self.ebi_files[0][1]
        if self.phys_offset is None :
            self.get_hw_id()
        if phys_offset is not None :
            print_out_str ("[!!!] Phys offset was set to {0:x}".format(phys_offset))
            self.phys_offset = phys_offset
        self.addr_to_symbol_dict = {}
        self.symbol_to_addr_dict = {}
        self.lookup_table = []
        self.page_offset = 0xc0000000
        self.config = []
        self.global_page_table = [0 for i in range(4096)]
        self.secondary_page_tables = [[0 for col in range(256)] for row in range(4096)]
        self.setup_symbol_tables()
        self.load_page_tables(ebi)
        self.qdss = None
        if not self.get_version() :
            print_out_str ("!!! Could not get the Linux version!")
            print_out_str ("!!! Your vmlinux is probably wrong for these dumps")
            print_out_str ("!!! Exiting now")
            sys.exit(1)
        if re.search('3\.0\.\d',self.version) is not None :
            self.setup_offset_table(offsets_common_3_0)
        if re.search('3\.4\.\d',self.version) is not None :
            self.setup_offset_table(offsets_common_3_4)
        if re.search('3\.7\.\d',self.version) is not None :
            self.setup_offset_table(offsets_common_3_7)
        if not self.get_config() :
           print_out_str ("!!! Could not get saved configuration")
           print_out_str ("!!! This is really bad and probably indicates RAM corruption")
           print_out_str ("!!! Some features may be disabled!")
        self.setup_offset_table(generic_mem_offsets)
        if self.is_config_defined("CONFIG_SPARSEMEM") or self.hw_id == 8960 or self.hw_id == 8064 :
           self.setup_offset_table(sparsemem_offsets)

    def dump_qdss(self) :
        out_dir = self.outdir
        if self.qdss is None :
             print_out_strt ("!!! QDSS was not setup to be dumped in this build!")
             return

        self.qdss.dump_all(self, out_dir)

    def get_config(self) :
        kconfig_addr = self.addr_lookup("kernel_config_data");
        if kconfig_addr is None :
            return
        kconfig_size = self.get_offset_struct("sizeof(kernel_config_data)","");
        # size includes magic, offset from it
        kconfig_size = kconfig_size - 16 -1
        zconfig = NamedTemporaryFile(mode='wb', delete=False)
        # kconfig data starts with magic 8 byte string, go past that
        s =  self.read_cstring(kconfig_addr, 8)
        if s != "IKCFG_ST" :
            return
        kconfig_addr = kconfig_addr + 8
        for i in range(0, kconfig_size) :
            val = self.read_byte(kconfig_addr + i)
            zconfig.write(struct.pack("<B",val))

        zconfig.close()
        zconfig_in = gzip.open(zconfig.name, 'rb')
        try:
            t = zconfig_in.readlines();
        except:
            return False
        zconfig_in.close()
        os.remove(zconfig.name)
        for l in t :
            self.config.append(l.rstrip().decode('ascii','ignore'))
        return True

    def print_config(self) :
        out_path = self.outdir
        saved_config = open(out_path+"/kconfig.txt","wb")

        for l in self.config :
            saved_config.write(l+"\n")

        saved_config.close()
        print_out_str("---wrote saved kernel config to {0}/kconfig.txt".format(out_path))

    def is_config_defined(self, config) :
        s = config+"=y"
        return s in self.config

    def get_version(self) :
        banner_addr = self.addr_lookup("linux_banner")
        if banner_addr is not None :
            # Don't try virt to phys yet, compute manually
            banner_addr = banner_addr - 0xc0000000 + self.phys_offset
            b = self.read_cstring(banner_addr, 256, False)
            if b is None :
                print_out_str ("!!! Could not read banner address!")
                return False
            v = re.search('Linux version (\d{0,2}\.\d{0,2}\.\d{0,2})',b)
            if v is None :
                print_out_str ("!!! Could not match version! {0}".format(b))
                return False
            self.version = v.group(1)
            print_out_str ("Linux Banner: "+b.rstrip())
            print_out_str ("version = {0}".format(self.version))
            return True
        else :
            print_out_str ("!!! Could not lookup banner address")
            return False

    def print_command_line(self) :
        command_addr = self.addr_lookup("saved_command_line")
        if command_addr is not None :
            command_addr = self.read_word(command_addr)
            b = self.read_cstring(command_addr, 2048)
            if b is None :
                print_out_str ("!!! could not read saved command line address")
                return False
            print_out_str ("Command Line: "+b)
            return True
        else :
            print_out_str ("!!! Could not lookup saved command line address")
            return False

    def auto_parse(self, file_path) :
        first_mem_path = None

        for f in first_mem_file_names :
            test_path = file_path+"/"+f
            if os.path.exists(test_path) :
                first_mem_path = test_path
                break

        if first_mem_path is None :
            print_out_str ("!!! Could not open a memory file. I give up")
            sys.exit(1)

        first_mem = open(first_mem_path, "rb")
        # put some dummy data in for now
        self.ebi_files = [(first_mem,0,0xffff0000,first_mem_path)]
        if not self.get_hw_id() :
            return False
        first_mem_end = self.ebi_start + os.path.getsize(first_mem_path) - 1
        self.ebi_files = [(first_mem,self.ebi_start,first_mem_end,first_mem_path)]
        print_out_str ("Adding {0} {1:x}--{2:x}".format(first_mem_path,self.ebi_start,first_mem_end))

        for f in extra_mem_file_names :
            extra_path = file_path+"/"+f

            if os.path.exists(extra_path) :
                extra = open(extra_path, "rb")
                extra_start = self.ebi_start + os.path.getsize(first_mem_path)
                extra_end = extra_start + os.path.getsize(extra_path) - 1
                print_out_str ("Adding {0} {1:x}--{2:x}".format(extra_path,extra_start,extra_end))
                self.ebi_files.append((extra, extra_start, extra_end, extra_path))

        #jaeseong.gim@lge.com
        if self.tz_start == 0xFE800000 :
            imemc_path = file_path+"/OCIMEM.BIN"
            if os.path.exists(imemc_path) :
                imemc = open(imemc_path,"rb")
                imemc_start = self.tz_start
                imemc_end = imemc_start + os.path.getsize(imemc_path) - 1
                print_out_str ("Adding {0} {1:x}--{2:x}".format(imemc_path,imemc_start,imemc_end))
                self.ebi_files.append((imemc,imemc_start,imemc_end,imemc_path))
                return True

        if self.imem_fname is not None :
            imemc_path = file_path+"/"+self.imem_fname
            if os.path.exists(imemc_path) :
                imemc = open(imemc_path,"rb")
                imemc_start = self.tz_start
                imemc_end = imemc_start + os.path.getsize(imemc_path) - 1
                print_out_str ("Adding {0} {1:x}--{2:x}".format(imemc_path,imemc_start,imemc_end))
                self.ebi_files.append((imemc,imemc_start,imemc_end,imemc_path))
        return True

    # TODO support linux launcher, for when linux T32 actually happens
    def create_t32_launcher(self) :
        out_path = self.outdir
        launch_config = open(out_path+"/t32_config.t32","wb")
        launch_config.write(launch_config_str.encode('ascii','ignore'))
        launch_config.close()

        startup_script = open(out_path+"/t32_startup_script.cmm","wb")

        startup_script.write("sys.cpu {0}\n".format(self.cpu_type).encode('ascii','ignore'))
        startup_script.write("sys.up\n".encode('ascii','ignore'))

        for ram in self.ebi_files :
            ebi_path = os.path.abspath(ram[3])
            startup_script.write("data.load.binary {0} 0x{1:x}\n".format(ebi_path, ram[1]).encode('ascii','ignore'))
        startup_script.write("PER.S.F C15:0x2 %L 0xFFFFC000 0x4000 0x{0:x}\n".format(self.phys_offset+0x4000).encode('ascii','ignore'))
        startup_script.write("mmu.on\n".encode('ascii','ignore'))
        startup_script.write("mmu.scan\n".encode('ascii','ignore'))
        startup_script.write(("data.load.elf "+os.path.abspath(self.vmlinux)+" /nocode\n").encode('ascii','ignore'))
        system_type = get_system_type()
        if system_type is 'Windows' :
            startup_script.write("task.config c:\\t32\\demo\\arm\\kernel\\linux\\linux.t32\n".encode('ascii','ignore'));
            startup_script.write("menu.reprogram c:\\t32\\demo\\arm\\kernel\\linux\\linux.men\n".encode('ascii','ignore'));
        else :
            startup_script.write("task.config /opt/t32/linux.t32\n".encode('ascii','ignore'));
            startup_script.write("menu.reprogram /opt/t32/linux.men\n".encode('ascii','ignore'));
        startup_script.write("task.dtask\n".encode('ascii','ignore'));
        startup_script.write("v.v  %ASCII %STRING linux_banner\n".encode('ascii','ignore'));
        if os.path.exists(out_path+"/regs_panic.cmm") :
            startup_script.write("do {0}\n".format(out_path+"/regs_panic.cmm").encode('ascii','ignore'))
        elif os.path.exists(out_path+"/core0_regs.cmm") :
            startup_script.write("do {0}\n".format(out_path+"/core0_regs.cmm").encode('ascii','ignore'))
        startup_script.close()

        t32_bat = open(out_path+"/launch_t32.bat","wb")
        t32_bat.write(("if \"%PROCESSOR_ARCHITECTURE%\"==\"x86\" (\n").encode('ascii','ignore'))
        t32_bat.write(("\tset T32_PATH=C:\\T32\\bin\\windows\n").encode('ascii','ignore'))
        t32_bat.write((") else (\n").encode('ascii','ignore'))
        t32_bat.write(("\tset T32_PATH=C:\\T32\\bin\\windows64\n").encode('ascii','ignore'))
        t32_bat.write((")\n").encode('ascii','ignore'))
        t32_bat.write(("start %T32_PATH%\\t32MARM.exe -c "+out_path+"/t32_config.t32, "+out_path+"/t32_startup_script.cmm").encode('ascii','ignore'))
        t32_bat.close()
        print_out_str ("--- Created a T32 Simulator launcher (run {0}/launch_t32.bat)".format(out_path))


    def read_tz_offset(self) :
        if self.tz_addr == 0 :
            print_out_str ("No TZ address was given, cannot read the magic value!")
            return None
        else :
            return self.read_word(self.tz_addr, False)

    def find_hw_id(self, socinfo_id, version) :
        if self.hw_version is not None :
            version = self.hw_version
        for cpuid in cpu_of_id:
            if socinfo_id == cpuid[0]:
                for hwid in hw_ids :
                      if cpuid[1] == hwid[HARDWARE_ID_IDX] :
                            if hwid[VERSION_COMPARE] is not None and hwid[VERSION_COMPARE] != version :
                                continue

                            return hwid
        return None


    def get_hw_id(self) :
        heap_toc_offset = self.get_offset_struct("((struct smem_shared *)0x0)", "heap_toc")
        if heap_toc_offset is None :
            print_out_str ("!!!! Could not get a necessary offset for auto detection!")
            print_out_str ("!!!! Please check the gdb path which is used for offsets!")
            print_out_str ("!!!! Also check that the vmlinux is not stripped")
            print_out_str ("!!!! Exiting...")
            sys.exit(1)

        smem_heap_entry_size = self.get_offset_struct("sizeof(struct smem_heap_entry)", "")
        offset_offset = self.get_offset_struct("((struct smem_heap_entry *)0x0)", "offset")
        socinfo_format = -1
        socinfo_id = -1
        socinfo_version = 0
        socinfo_build_id = "DUMMY"
        hwid = None

        if (self.hw_id is None) :
            for smem_offset in smem_offsets :
                socinfo_start_addr = self.ebi_files[0][1] + smem_offset + heap_toc_offset + smem_heap_entry_size*SMEM_HW_SW_BUILD_ID + offset_offset
                soc_start = self.read_word(socinfo_start_addr, False)
                if soc_start is None :
                    continue

                socinfo_start = self.ebi_files[0][1] + smem_offset + soc_start

                socinfo_format = self.read_word(socinfo_start, False)
                socinfo_id = self.read_word(socinfo_start + 4, False)
                socinfo_version = self.read_word(socinfo_start + 8, False)
                socinfo_build_id = self.read_cstring(socinfo_start + 12, BUILD_ID_LENGTH, False)

                if socinfo_id is not None and socinfo_version is not None :
                    hwid = self.find_hw_id(socinfo_id, socinfo_version >> 16)
                if (hwid is not None) :
                    break
            if (hwid is None) :
                print_out_str ("!!!! Could not find hardware")
                print_out_str ("!!!! The SMEM didn't match anything")
                print_out_str ("!!!! You can use --force-hardware to use a specific set of values")
                sys.exit(1)

        else :
            hwid = None
            for a in hw_ids :
                if self.hw_id == a[HARDWARE_ID_IDX] and self.hw_version == a[VERSION_COMPARE]:
                    print_out_str ("!!! Hardware id found! The socinfo values given are bogus")
                    print_out_str ("!!! Proceed with caution!")
                    hwid = a
                    break
            if hwid is None :
                print_out_str ("!!! A bogus hardware id was specified: {0}".format(self.hw_id))
                print_out_str ("!!! Try passing one of these to --force-hardware.")
                print_out_str ("!!! If a version is specified, pass the version with --force-version")
                for a in hw_ids :
                    if a[VERSION_COMPARE] is not None :
                        v = "v{0}".format(a[VERSION_COMPARE])
                    else :
                        v = ""
                    print_out_str ("!!!    {0}{1}".format(a[HARDWARE_ID_IDX], v))
                sys.exit(1)

        print_out_str ("\nHardware match: {0}".format(hwid[HARDWARE_ID_IDX]))
        print_out_str ("Socinfo id = {0}, version {1:x}.{2:x}".format(socinfo_id, socinfo_version >> 16, socinfo_version & 0xFFFF))
        print_out_str ("Socinfo build = {0}".format(socinfo_build_id))
        print_out_str ("Now setting phys_offset to {0:x}".format(hwid[PHYS_OFFSET_IDX]))
        print_out_str ("TZ address: {0:x}".format(hwid[WATCHDOG_BARK_OFFSET_IDX]))
        self.phys_offset = hwid[PHYS_OFFSET_IDX]
        self.tz_addr = hwid[WATCHDOG_BARK_OFFSET_IDX]
        self.ebi_start = hwid[MEMORY_START_IDX]
        self.tz_start = hwid[IMEM_START_IDX]
        self.hw_id = hwid[HARDWARE_ID_IDX]
        self.cpu_type = hwid[CPU_TYPE]
        self.imem_fname = hwid[IMEM_FILENAME]
        return True



    # offsets necessary for dumping task information
    def setup_offset_table(self, offsets_req, silent=False) :
        gdb_cmd = NamedTemporaryFile(mode='w+t', delete=False)
        for e in offsets_req :
            if e[3] > 0 :
                gdb_cmd.write("print /x {0}\n".format(e[0]))
            else :
                gdb_cmd.write("print &{0}.{1}\n".format(e[0],e[1]))
        gdb_cmd.flush()
        gdb_cmd.close()
        cmd = "{0} -x {1} --batch {2}".format(self.gdb_path, gdb_cmd.name, self.vmlinux)
        args = cmd.split(' ')
        p = subp.Popen(args, stdout=subp.PIPE, stderr=subp.PIPE)
        (results, err) = p.communicate()
        results = results.splitlines()

        if not silent:
            if len(err) > 0:
                print_out_str(err)

        for r,v in zip(results,offsets_req) :
            m = re.search('(0x[0-9a-f]+)',r)
            if m is not None:
                try :
                    val = int(m.group(0),16)
                except ValueError:
                    continue
                self.offset_table.append((v[0],v[1],v[3],val))
        os.remove(gdb_cmd.name)

    # return the preloaded offset of a given structure
    def get_offset_struct(self, sym, member) :
        for r in self.offset_table :
            if (r[0] == sym) and (r[1] == member) :
                return r[3]
        return None

    def load_page_tables(self, ebi) :
        msm_ttbr0 = self.phys_offset + 0x4000
        virt_address = 0x0
        gb_i = 0
        se_i = 0
        for l1_pte_ptr in range(msm_ttbr0,msm_ttbr0+(4096*4),4) :
            l1_pte = self.read_word(l1_pte_ptr, False)
            self.global_page_table[gb_i] = l1_pte
            if l1_pte is None :
                gb_i+=1
                continue
            if (l1_pte & 3) == 0 or (l1_pte & 3) == 3 :
                for k in range(0, 256) :
                    virt_address += 0x1000
            elif (l1_pte & 3) == 2 :
                if ((l1_pte & 0x40000) == 0) :
                    l1_pte_counter = l1_pte & 0xFFF00000
                    for k in range (0, 256) :
                        virt_address += 0x1000
                        l1_pte_counter += 0x1000
                else :
                    gb_i+=1
                    continue
            elif (l1_pte & 3) == 1 :
                l2_pt_desc = l1_pte
                l2_pt_base = l2_pt_desc & (~0x3ff)
                for l2_pte_ptr in range(l2_pt_base,l2_pt_base+(256*4), 4) :
                    virt_address+=0x1000
                    l2_pt_entry = self.read_word(l2_pte_ptr, False)
                    self.secondary_page_tables[gb_i][se_i] = l2_pt_entry
                    se_i+=1
                se_i=0
            gb_i+=1

    def bm (self, msb, lsb) :
        a = c_uint((0xFFFFFFFF << (31 - msb))).value
        return c_uint(((a >> (31 - msb + lsb)) << lsb)).value

    def bvalsel(self, msb, lsb, val) :
        return ((val & self.bm(msb, lsb)) >> lsb)

    # TODO add --force-bad-pagetables
    def virt_to_phys(self, virt) :
        if virt is None :
            return None
        global_offset = self.bvalsel(31, 20, virt)
        l1_pte = self.global_page_table[global_offset]
        bit18 =  (l1_pte & 0x40000) >> 18
        if (self.bvalsel(1,0,l1_pte) == 1) :
            l2_offset = self.bvalsel(19,12, virt)
            l2_pte = self.secondary_page_tables[global_offset][l2_offset]
            if l2_pte is None :
                return None
            if (self.bvalsel(1,0,l2_pte)  == 2) or (self.bvalsel(1,0,l2_pte) == 3) :
                entry4kb = (l2_pte & self.bm(31,12)) + self.bvalsel(11,0,virt)
                return entry4kb
            elif (self.bvalsel(1,0,l2_pte) == 1) :
                entry64kb = (l2_pte & self.bm(31,16)) + self.bvalsel(15,0,virt)
                return entry64kb
        if (self.bvalsel(1,0,l1_pte) == 2) :
            onemb_entry = self.bm(31,20) & l1_pte
            onemb_entry += self.bvalsel(19,0,virt)
            return onemb_entry

        return 0


    def setup_symbol_tables(self) :
        stream = os.popen(self.nm_path+" -n "+ self.vmlinux)
        symbols = stream.readlines()
        for line in symbols :
            s = line.split(' ')
            if len(s) == 3:
                self.addr_to_symbol_dict[int(s[0],16)] = s[2].rstrip()
                self.symbol_to_addr_dict[s[2].rstrip()] = int(s[0],16)
                self.lookup_table.append((int(s[0],16),s[2].rstrip()))
        stream.close()

    def addr_lookup(self, symbol) :
        if symbol in self.symbol_to_addr_dict:
            return self.symbol_to_addr_dict[symbol]

    def symbol_lookup(self, addr) :
        if addr in self.addr_to_symbol_dict:
            return self.addr_to_symbol_dict[addr]

    def dump_symbol_table(self) :
        for k,v, in self.addr_to_symbol_dict.items():
            print_out_str (v)

    def unwind_lookup(self, addr, symbol_size = 0) :
        if (addr is None) :
            return ("(Invalid address)", 0x0)

        # modules are not supported so just print out an address
        # instead of a confusing symbol
        if (addr < self.page_offset) :
            return ("(No symbol for address {0:x})".format(addr), 0x0)

        low = 0
        high = len(self.lookup_table)
        # Python now complains about division producing floats
        mid = (low+high) >> 1
        premid = 0

        while(not(addr >= self.lookup_table[mid][0] and addr < self.lookup_table[mid+1][0])) :

            if(addr < self.lookup_table[mid][0]) :
                           high = mid - 1

            if(addr > self.lookup_table[mid][0]) :
                low = mid + 1

            mid = (high+low) >> 1

            if(mid==premid) :
                return None
            if (mid +1) >= len(self.lookup_table) or mid < 0 :
                return None

            premid = mid

        if symbol_size == 0 :
            return (self.lookup_table[mid][1], addr - self.lookup_table[mid][0])
        else :
            return (self.lookup_table[mid][1], self.lookup_table[mid+1][0] - self.lookup_table[mid][0])

    def read_physical(self, addr, length, trace = False) :
        ebi = (-1, -1, -1)
        for a in self.ebi_files :
            fd, start, end , path = a
            if addr >= start and addr < end :
                ebi = a
                break
        if ebi[0] is -1 :
            return None
        if trace :
            print_out_str ("reading from {0}".format(ebi[0]))
            print_out_str ("start = {0:x}".format(ebi[1]))
            print_out_str ("end = {0:x}".format(ebi[2]))
            print_out_str ("length = {0:x}".format(length))
        offset = addr - ebi[1]
        if trace :
            print_out_str ("offset = {0:x}".format(offset))
        ebi[0].seek(offset)
        a = ebi[0].read(length)
        if trace :
            print_out_str ("result = {0}".format(a))
            print_out_str ("lenght = {0}".format(len(a)))
        return a

    def read_dword(self, address, virtual = True, trace = False) :
        if trace :
            print_out_str ("reading {0:x}".format(address))
        s = self.read_string(address, "<Q", virtual, trace)
        if s is None :
            return None
        else :
            return s[0]

    # returns the 4 bytes read from the specified virtual address
    # return None on error
    def read_word(self, address, virtual = True, trace = False) :
        if trace :
            print_out_str ("reading {0:x}".format(address))
        s = self.read_string(address, "<I", virtual, trace)
        if s is None :
            return None
        else :
            return s[0]

    def read_halfword(self, address, virtual = True, trace = False) :
        if trace :
            print_out_str ("reading {0:x}".format(address))
        s = self.read_string(address, "<H", virtual, trace)
        if s is None :
            return None
        else :
            return s[0]

    def read_byte(self, address, virtual = True, trace = False) :
        if trace :
            print_out_str ("reading {0:x}".format(address))
        s = self.read_string(address, "<B", virtual, trace)
        if s is None :
            return None
        else :
            return s[0]

    def read_cstring(self, address, max_length, virtual = True) :
        addr = address
        if virtual :
            addr = self.virt_to_phys(address)
        s = self.read_physical(addr, max_length)
        if s is not None :
            a = s.decode('ascii','ignore')
            return a.split('\0')[0]
        else :
            return s

    # returns a tuple of the result from reading from the specified fromat string
    # return None on failure
    def read_string(self, address, format_string, virtual = True, trace = False) :
        addr = address
        if virtual :
            addr = self.virt_to_phys(address)
        if trace :
            print_out_str ("reading from phys {0:x}".format(addr))
        s = self.read_physical(addr, struct.calcsize(format_string), trace)
        if (s is None) or (s == ""):
            if trace :
                print_out_str ("address {0:x} failed hard core (v {1} t{2})".format(addr, virtual, trace))
            return None
        return struct.unpack(format_string,s)

