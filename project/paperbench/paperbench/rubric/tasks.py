from dataclasses import dataclass, field, replace
from typing import Optional, Sequence, TypeVar, cast

from paperbench.rubric.utils import get_openai_client, random_id
from paperbench.utils import get_logger, oai_completion_with_retry

VALID_TASK_CATEGORIES = {
    "Code Development",
    "Code Execution",
    "Result Analysis",
    "Subtree",
}

TASK_CATEGORY_QUESTIONS = {
    "Code Development": (
        "Does the code in the submission contain a correct implementation of this?"
        " Note: mere instructions or descriptions of implementations are not sufficient;"
        " you should check whether there is actual code that implements the requirement."
    ),
    "Code Execution": "Does running the reproduce.sh script lead to this being successfully executed?",
    "Result Analysis": "Did the reproduce.sh script execution produce evidence that agrees with these results?",
    "Subtree": "What is the weighted score of all the criteria in the subtree?",
}

logger = get_logger(__name__)

T = TypeVar("T", bound="TaskNode")  # This can be TaskNode or any subclass of TaskNode


@dataclass(frozen=True, kw_only=True)
class TaskNode:
    id: str
    requirements: str
    weight: int
    sub_tasks: Sequence["TaskNode"] = field(default_factory=list)
    task_category: str | None = None

    def __post_init__(self):
        if not isinstance(self.weight, (int, float)):
            raise ValueError("Weight must be a number.")

        if self.weight <= 0:
            raise ValueError("Weight must be a positive number.")

        if self.task_category and self.task_category not in VALID_TASK_CATEGORIES:
            # TODO: bring back error after we finalize all rubrics
            logger.warning(f"Invalid task category: {self.task_category}")
            # raise ValueError(f"Invalid task category: {self.task_category}")

        if not self.is_leaf() and self.task_category:
            raise ValueError(f"Non-leaf node '{self.id}' cannot have a task category.")

        if self.is_leaf() and not self.task_category:
            # TODO: bring back error after we finalize all rubrics
            logger.warning(f"Leaf node '{self.id}' doesn't have a task category.")
            # raise ValueError(f"Leaf node '{self.id}' doesn't have a task category.")

    def is_leaf(self) -> bool:
        """Check if the node is a leaf node (has no sub-tasks)."""

        return len(self.sub_tasks) == 0

    def find(self, node_id: str) -> "TaskNode":
        """Searches for a node with `node_id` depth-first, throwing an error if it doesn't exist."""

        if self.id == node_id:
            return self

        for sub_task in self.sub_tasks:
            try:
                return sub_task.find(node_id)
            except ValueError:
                continue

        raise ValueError(f"Task with id '{node_id}' not found.")

    def get_parent(self, node_id: str) -> "TaskNode":
        """Finds the parent of the node with `node_id`."""

        if self.id == node_id:
            raise ValueError("The root node has no parent.")

        for sub_task in self.sub_tasks:
            if sub_task.id == node_id:
                return self
            try:
                return sub_task.get_parent(node_id)
            except ValueError:
                continue

        raise ValueError(f"Node with id '{node_id}' not found. Can't find its parent.")

    def contains(self, node_id: str) -> bool:
        """Returns `True` iff a node with `node_id` appears in the tree."""

        try:
            self.find(node_id)
        except ValueError:
            return False
        return True

    def replace(self, node_id: str, new_node: "TaskNode") -> "TaskNode":
        """Replace the node with `node_id`, throwing an error if it doesn't exist."""

        if not self.contains(node_id):
            raise ValueError(f"Task with id '{node_id}' not found in the task tree.")

        return self._replace(node_id, new_node)

    def _replace(self, node_id: str, new_node: "TaskNode") -> "TaskNode":
        """Replace the node with `node_id`, if it exists."""

        if self.id == node_id:
            return new_node

        new_sub_tasks = []
        for sub_task in self.sub_tasks:
            new_sub_task = sub_task._replace(node_id, new_node)
            new_sub_tasks.append(new_sub_task)

        return replace(self, sub_tasks=new_sub_tasks)

    def delete(self, node_id: str) -> Optional["TaskNode"]:
        """Deletes the node with `node_id` from the tree."""

        if self.id == node_id:
            return None

        new_sub_tasks = []
        for sub_task in self.sub_tasks:
            new_sub_task = sub_task.delete(node_id)
            if new_sub_task is None:
                continue
            new_sub_tasks.append(new_sub_task)

        return replace(self, sub_tasks=new_sub_tasks)

    def set_sub_tasks(self, new_sub_tasks: list["TaskNode"]) -> "TaskNode":
        task_category = None if len(new_sub_tasks) > 0 else self.task_category
        return replace(self, sub_tasks=new_sub_tasks, task_category=task_category)

    def set_requirements(self, new_requirements: str) -> "TaskNode":
        return replace(self, requirements=new_requirements)

    def set_weight(self, new_weight: int) -> "TaskNode":
        return replace(self, weight=new_weight)

    def set_id(self, new_id: str) -> "TaskNode":
        return replace(self, id=new_id)

    def set_explanation(self, new_explanation: str) -> "TaskNode":
        return replace(self, explanation=new_explanation)

    def add_sub_task(self, new_sub_task: "TaskNode") -> "TaskNode":
        """Adds a new sub-task to the current node."""

        new_sub_tasks = list(self.sub_tasks) + [new_sub_task]
        return replace(self, sub_tasks=new_sub_tasks, task_category=None)

    def set_task_category(self, new_task_category: str) -> "TaskNode":
        return replace(self, task_category=new_task_category)

    @classmethod
    def from_dict(cls, data: dict) -> "TaskNode":
        try:
            sub_tasks = [cls.from_dict(task) for task in data["sub_tasks"]]
            task = TaskNode(
                id=data["id"],
                requirements=data["requirements"],
                weight=data["weight"],
                sub_tasks=sub_tasks,
                task_category=data.get("task_category"),
            )
        except KeyError as e:
            node_id = data.get("id", "unknown")
            raise ValueError(f"Missing required field in node '{node_id}': {e}")
        return task

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "requirements": self.requirements,
            "weight": self.weight,
            "sub_tasks": [task.to_dict() for task in self.sub_tasks],
            "task_category": self.task_category,
        }

    def find_path_to_descendant(self, descendant_id: str) -> list["TaskNode"] | None:
        """Returns the path from the current node to the node with `descendant_id`."""

        if self.id == descendant_id:
            return [self]
        for sub_task in self.sub_tasks:
            sub_path = sub_task.find_path_to_descendant(descendant_id)
            if sub_path:
                return [self] + sub_path
        return None

    def get_prior_nodes(
        self, root: "TaskNode", max_prior_nodes: int | None = None
    ) -> list["TaskNode"]:
        """
        Returns all (or a `max_prior_nodes` number of, if specified) nodes that are either:
        - Ancestors of the current node,
        - Preceding siblings of the current node, or
        - Preceding siblings of an ancestor.

        Example:
            For the following tree:

            ```
            A
            ├── B
            │   ├── D
            │   └── E
            └── C
                ├── F
                └── G
            ```

            Calling `get_prior_nodes` on node "G" with "A" as the root will return:

            ```
            ["A", "B", "C", "F"]
            ```

            Explanation:
            - "A" is an ancestor of "G".
            - "B" is a preceding sibling of an ancestor, "C".
            - "C" is an ancestor of "G".
            - "F" is a preceding sibling of the current node, "G".
        """

        if self.id == root.id:
            return []

        path = root.find_path_to_descendant(self.id)
        if path is None:
            raise ValueError(f"Task with id '{self.id}' not found.")

        required_nodes = [root]  # Start with the root node
        for i in range(1, len(path)):  # Start from the first child of the root
            node, parent = path[i], path[i - 1]
            node_siblings = parent.sub_tasks
            node_siblings_ids = [i.id for i in node_siblings]

            this_node_idx = node_siblings_ids.index(node.id)
            # only keep this node +  _preceding_ siblings;  _subsequent_ siblings do not affect `self`.
            required_nodes += node_siblings[: this_node_idx + 1]

        required_nodes = required_nodes[:-1]  # Don't include the target node
        if max_prior_nodes is not None:
            required_nodes = required_nodes[-max_prior_nodes:]
        return required_nodes

    def get_descendants_depth_first(self) -> list["TaskNode"]:
        """
        Returns all descendants of the current node, in depth-first order.
        """
        descendants = []
        for sub_task in self.sub_tasks:
            descendants.append(sub_task)
            descendants += sub_task.get_descendants_depth_first()
        return descendants

    def get_descendants_with_duplicate_ids(self) -> list["TaskNode"]:
        """
        Returns all descendants with duplicate IDs.
        """
        descendants = self.get_descendants_depth_first()
        node_ids = [node.id for node in descendants]
        duplicate_ids = {id for id in node_ids if node_ids.count(id) > 1}
        return [descendant for descendant in descendants if descendant.id in duplicate_ids]

    def get_leaf_nodes(self: T) -> list[T]:
        """
        Returns all leaf nodes in the tree in depth-first order.
        """
        if self.is_leaf():
            return [self]
        return [
            leaf_node
            for sub_task in self.sub_tasks
            for leaf_node in cast(list[T], sub_task.get_leaf_nodes())
        ]

    def prune_to_depth(self, max_depth: int, current_depth: int = 0) -> "TaskNode":
        """
        Returns a new TaskNode with the tree pruned to the specified maximum depth.
        The root node is at depth 0.
        """
        if current_depth >= max_depth:
            # Create a leaf node with a task category if we're pruning
            return TaskNode(
                id=self.id,
                requirements=self.requirements,
                weight=self.weight,
                sub_tasks=[],
                task_category=self.task_category,
            )

        # Recursively prune sub-tasks
        new_sub_tasks = [
            sub_task.prune_to_depth(max_depth, current_depth + 1) for sub_task in self.sub_tasks
        ]

        return TaskNode(
            id=self.id,
            requirements=self.requirements,
            weight=self.weight,
            sub_tasks=new_sub_tasks,
            task_category=self.task_category,
        )

    def duplicate_with_new_ids(self) -> "TaskNode":
        """Creates a deep copy of the node with new IDs for all nodes in the tree."""
        new_sub_tasks = [task.duplicate_with_new_ids() for task in self.sub_tasks]
        return replace(self, id=random_id(), sub_tasks=new_sub_tasks)

    def code_only(self) -> Optional["TaskNode"]:
        """
        Returns a new tree (or `None`) where any leaf node not labeled
        'Code Development' is removed. Internal nodes are kept only if
        they have at least one valid child after pruning.
        """
        return reduce_to_category(self, "Code Development")


def reduce_to_category(node: TaskNode, category: str) -> TaskNode | None:
    """
    Returns a new tree (or `None`) where any leaf node not labeled
    `category` is removed. Internal nodes are kept only if
    they have at least one valid child after pruning.
    """
    if node.is_leaf():
        if node.task_category == category:
            return node
        return None

    filtered_sub_tasks = []
    for st in node.sub_tasks:
        pruned = reduce_to_category(st, category)
        if pruned is not None:
            filtered_sub_tasks.append(pruned)

    # need this to drop trees that don't contain any `category`
    if not filtered_sub_tasks and node.task_category != category:
        return None

    return replace(node, sub_tasks=filtered_sub_tasks)


def generate_task_category(node: TaskNode, model: str = "gpt-4o") -> str:
    """Uses an LLM to generate a task category for the given `node` based on its `requirements`."""

    client = get_openai_client()

    messages = [
        {
            "role": "system",
            "content": (
                "You are an assistant that classifies tasks into predefined categories. "
                "The categories are:\n"
            )
            + "\n".join(f"- {category}" for category in VALID_TASK_CATEGORIES)
            + "\n\n"
            + (
                "Please read the following task requirement and determine the most appropriate "
                "category from the list above. Respond with only the category name, exactly as "
                "written."
            ),
        },
        {
            "role": "user",
            "content": f"Task requirement: {node.requirements}",
        },
    ]
    completion = oai_completion_with_retry(
        client.chat.completions.create,
        messages=messages,
        model=model,
    )
    response = completion.choices[0].message.content.strip()

    if response not in VALID_TASK_CATEGORIES:
        raise ValueError(f"Invalid task category generated: {response}")

    return response
