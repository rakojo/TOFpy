# from timeit import default_timer as timer
import cProfile
import pstats

profiler = cProfile.Profile()

def start():
    global profiler
    profiler.enable()


def stop():
    global profiler
    profiler.disable()
    # Save the profiling results to a file


def save():
    global profiler
    with open('profile_results_2.prof', 'w') as f:
        print('Profiling results saved to profile_results.prof')
        ps = pstats.Stats(profiler, stream=f)
        ps.sort_stats(pstats.SortKey.NAME)
        ps.reverse_order()
        ps.print_stats()




