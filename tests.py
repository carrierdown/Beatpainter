import helpers

nums = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
norm_nums = helpers.normalize(nums, 50, 100)
print(norm_nums)
print("closest index is:", helpers.get_closest_index(norm_nums, 49),
      norm_nums[helpers.get_closest_index(norm_nums, 49)])
