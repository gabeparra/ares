# Test file for Glup code review
def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# This is inefficient - it recalculates values multiple times
# Can you suggest a better implementation?

print(calculate_fibonacci(10))
