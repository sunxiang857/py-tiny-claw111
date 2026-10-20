# internal/tools/bash.py
# 对应 Go 版: internal/tools/bash.go
# 第 6 章：bash 工具 —— Agent 最强大的"万能手"，可以执行任意 shell 命令。
import json
import subprocess

from internal.schema.message import ToolDefinition
from internal.tools.registry import BaseTool


class BashTool(BaseTool):
    def __init__(self, work_dir: str):
        self.work_dir = work_dir

    def name(self) -> str:
        return "bash"

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name(),
            description="在当前工作区执行任意的 bash 命令。支持链式命令(如 &&)。返回标准输出(stdout)和标准错误(stderr)。",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要执行的 bash 命令",
                    },
                },
                "required": ["command"],
            },
        )

    def execute(self, args: str) -> str:
        try:
            input_args = json.loads(args)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"参数解析失败: {e}") from e

        # ==================================================
        # 要求（bash 工具的 4 个 Harness 逻辑边界）：
        # 1. 工作区约束：用 subprocess.run(["bash", "-c", 命令], cwd=self.work_dir, ...)
        #    执行命令，并捕获 stdout 和 stderr（capture_output=True, text=True）
        # 2. 超时控制：timeout=30；捕获 subprocess.TimeoutExpired，
        #    返回已有输出 + "\n[警告: 命令执行超时(30s)，已被系统强制终止。]"
        # 3. 自纠错回传：returncode 非 0 时不要抛异常，而是返回
        #    "执行报错: exit status 退出码\n输出:\n" + 合并后的输出
        # 4. 输出为空时返回 "命令执行成功，无终端输出。"
        # 5. 输出超过 8000 字符时截断，并追加截断提示
        # ==================================================
        command = input_args.get("command", "")

        MAX_LEN = 8000
        try:
            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except subprocess.TimeoutExpired as e:
            # 超时：把已经产生的输出返回，并追加超时提示
            partial = (e.stdout or "") + (e.stderr or "")
            if isinstance(partial, bytes):
                partial = partial.decode("utf-8", errors="replace")
            return partial + "\n[警告: 命令执行超时(30s)，已被系统强制终止。]"

        output_str = (proc.stdout or "") + (proc.stderr or "")

        # 自纠错回传：非零退出码不抛异常，原样返回错误
        if proc.returncode != 0:
            return f"执行报错: exit status {proc.returncode}\n输出:\n{output_str}"

        if output_str == "":
            return "命令执行成功，无终端输出。"

        if len(output_str) > MAX_LEN:
            return f"{output_str[:MAX_LEN]}\n\n...[终端输出过长，已截断至前 {MAX_LEN} 字节]..."

        return output_str
