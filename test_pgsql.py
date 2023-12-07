# Пример использования:
from icecream import ic



example= {
    "recipedata": [
        {
            "Automate": "ns=4, s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.RecipesStruct.Recipes[1].Automate",
            "Cycle": "ns=4, s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.RecipesStruct.Recipes[1].Cycle",
        },
        {
            "Automate": "ns=4, s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.RecipesStruct.Recipes[2].Automate",
            "Cycle": "ns=4, s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.RecipesStruct.Recipes[2].Cycle",
        },
    ],
    "values": {
        "Light room 1": "ns=4; s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.LightRoom1",
        "Light room 2": "ns=4; s=|var|WAGO 750-8202 PFC200 2ETH RS.Application.GVL.LightRoom2",
    },
}
def find_substring_path(data, substring):
    def search_path(current_data, current_path):
        if isinstance(current_data, dict):
            for key, value in current_data.items():
                new_path = f"{current_path}.{key}" if current_path else key
                if isinstance(value, dict) or isinstance(value, list):
                    result = search_path(value, new_path)
                    if result:
                        return result
                elif isinstance(value, str) and substring in value:
                    return new_path, current_data
        elif isinstance(current_data, list):
            for i, item in enumerate(current_data):
                new_path = f"{current_path}[{i}]"
                result = search_path(item, new_path)
                if result:
                    return result
        return None

    return search_path(data, "")

custom_dict = CustomDict(example)
ic(custom_dict)
# Использование метода get_child
path_to_find = "recipedata[1].Automate"
result = custom_dict.get_child(path_to_find)

if result is not None:
    print(f"Значение по пути '{path_to_find}': {result}")
else:
    print(f"Путь '{path_to_find}' не найден.")