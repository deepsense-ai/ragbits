import hydra
import random
from omegaconf import DictConfig, OmegaConf

from ragbits.evaluate.optimizer import Optimizer


@hydra.main(config_path="config", config_name="retrieval", version_base="3.2")
def main(config: DictConfig) -> None:
    """
    Function running evaluation for all datasets and evaluation tasks defined in hydra config.

    Args:
        config: Hydra configuration.
    """
    optimizer = Optimizer()
    optimizer.optimize(config, "dupa", "dupa")




def extract_random_opt_params_range(cfg: DictConfig, result=None) -> dict:
    """
    Returns a new dictionary with the keys that contain 'opt_params_range' replaced
    by random numbers between the specified range [A, B].
    """
    result = {}
    for key, value in cfg.items():
        if isinstance(value, DictConfig):
            nested_result = extract_random_opt_params_range(value, result)
            if nested_result:  # Only add if nested_result is not empty
                result[key] = nested_result
        elif key == "opt_params_range":
            res = random.uniform(value[0], value[1])
            return res  # Return single random value if opt_params_range is found
    return result

# Example usage

# def extract_random_opt_params_range(cfg: DictConfig) -> dict:
#     """
#     Returns a new dictionary with keys that contain 'opt_params_range'
#     replaced by random numbers from the specified range [A, B].
#     """
#     result = {}
#
#     def recursive_search(current_cfg, path):
#         for key, value in current_cfg.items():
#             current_path = path + [key]
#             if isinstance(value, DictConfig):
#                 recursive_search(value, current_path)
#             elif key == "opt_params_range" and isinstance(value, list) and len(value) == 2:
#                 # Generate random number in range [A, B] and add to result dict
#                 result[".".join(current_path[:-1])] = random.uniform(value[0], value[1])
#
#     # Start recursive search from the root level
#     recursive_search(cfg, [])
#
#     return result

cfg = OmegaConf.create({
    "layer1": {
        "opt_params_range": [10, 20],
        "other_key": "value"
    },
    "layer2": {
        "sub_layer": {
            "opt_params_range": [5, 15],
            "yet_another_key": "another_value"
        }
    }
})
z = 1

# Create a new dictionary with replaced values
new_cfg = extract_random_opt_params_range(cfg)

print(new_cfg)

# Example usage


main()