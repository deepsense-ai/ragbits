import { Task } from "@ragbits/api-client-react";

export interface TaskNode extends Task {
  children: TaskNode[];
}

export class TaskTree {
  private nodes: Map<string, TaskNode> = new Map();
  private roots: TaskNode[] = [];

  constructor(tasks: Task[]) {
    this.buildTree(tasks);
  }

  private buildTree(tasks: Task[]) {
    for (const task of tasks) {
      this.nodes.set(task.id, { ...task, children: [] });
    }

    for (const node of this.nodes.values()) {
      if (node.parent_id) {
        const parent = this.nodes.get(node.parent_id);
        if (parent) {
          parent.children.push(node);
          parent.children.sort((a, b) => a.order - b.order);
        } else {
          this.roots.push(node);
          this.roots.sort((a, b) => a.order - b.order);
        }
      } else {
        this.roots.push(node);
        this.roots.sort((a, b) => a.order - b.order);
      }
    }
  }

  *iterate(): IterableIterator<TaskNode> {
    function* dfs(nodes: TaskNode[]): IterableIterator<TaskNode> {
      for (const node of nodes) {
        yield node;
        yield* dfs(node.children);
      }
    }
    yield* dfs(this.roots);
  }

  get(id: string): TaskNode | undefined {
    return this.nodes.get(id);
  }

  update(id: string, updates: Partial<Task>): void {
    const node = this.nodes.get(id);
    if (!node) return;

    Object.assign(node, updates);
    if (updates.order !== undefined) {
      if (node.parent_id) {
        const parent = this.nodes.get(node.parent_id);
        parent?.children.sort((a, b) => a.order - b.order);
      } else {
        this.roots.sort((a, b) => a.order - b.order);
      }
    }

    if (updates.status === "completed") {
      this.completeChildren(node);
    }
  }

  private completeChildren(node: TaskNode) {
    for (const child of node.children) {
      child.status = "completed";
      this.completeChildren(child);
    }
  }

  getRoots(): TaskNode[] {
    return this.roots;
  }
}
