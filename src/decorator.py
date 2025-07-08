import time
from functools import wraps

from src.utils.config import cfg_engine
from src.utils.utils import logger


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        elapsed_time = end - start
        logger.info(f"Execution time of {func.__name__}(): {elapsed_time:.4f} seconds")

        # Save elapsed time
        if "elapsed_times" in cfg_engine:
            cfg_engine.elapsed_times.setdefault(func.__name__, []).append(elapsed_time)
        return result

    return wrapper


def debug(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(
            f"Function {func.__name__}() called with args: {args} and kwargs: {kwargs}"
        )
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        logger.info(f"Function {func.__name__}() returned: {result}")
        logger.info(f"Execution time of {func.__name__}(): {end - start:.4f} seconds")
        return result

    return wrapper


def retry(total_try_cnt=5, sleep_in_sec=0, retryable_exceptions=(Exception)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for cnt in range(total_try_cnt):
                logger.info(f"trying {func.__name__}() [{cnt+1}/{total_try_cnt}]")

                try:
                    result = func(*args, **kwargs)
                    logger.info(f"in retry(), {func.__name__}() returned '{result}'")

                    if result:
                        return result
                except retryable_exceptions as e:
                    logger.info(
                        f"in retry(), {func.__name__}() raised retryable exception '{e}'"
                    )
                    pass
                except Exception as e:
                    logger.info(f"in retry(), {func.__name__}() raised {e}")
                    raise e

                time.sleep(sleep_in_sec)
            logger.info(f"{func.__name__} finally has been failed")

        return wrapper

    return decorator


def safe_return(default=dict()):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                logger.info(f"in safe_return(), {func.__name__}() raised {e}")
                result = default

            return result

        return wrapper

    return decorator
