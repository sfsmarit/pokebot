import os
import importlib.util


def run_all_functions_in_directory(directory) -> list[str]:
    failed_modules = []

    for i, filename in enumerate(os.listdir(directory)):
        if filename.endswith(".py") and filename != "__init__.py":
            filepath = os.path.join(directory, filename)
            module_name = os.path.splitext(filename)[0]

            # モジュールをファイルパスから読み込む
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # モジュール名と同じ関数を実行
            func = getattr(module, module_name, None)
            if callable(func):
                res = func()
                print(f"{i+1}\t{module_name}\t{res}")
                if not res:
                    failed_modules.append(module_name)
            else:
                print(f"{i+1}\t{module_name}\tNot found")

    return failed_modules


if __name__ == "__main__":
    res = run_all_functions_in_directory("./tests/ability/")
    print("-"*50)
    print("FAIL" if res else "PASS")
    for i, s in enumerate(res):
        print(f"{i+1}\t{s}")
