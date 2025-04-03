import multiprocessing

bind = "0.0.0.0:10000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
timeout = 120
