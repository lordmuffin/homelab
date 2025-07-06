# Claude Command: /bump

## Description

As a developer, I want to add a minor, non-functional change (a timestamped comment) to all of my Gitea pipeline files to trigger a new run, and then commit these changes automatically.

## Usage

`/bump`

## What the command does

This command performs the following actions in order:

1.  **Finds Pipeline Files**: It recursively searches the entire workspace for files located in a `.gitea/workflows/` directory that end with a `.yml` or `.yaml` extension.
2.  **Adds Timestamp**: For each file found, it appends a new comment line at the end of the file. This comment includes the current date and time, for example: `# Bumped on: 2025-07-07 10:30:00 UTC`. This trivial change is enough to make Git recognize the file as modified.
3.  **Executes Commit**: After modifying all the pipeline files, the command will automatically execute the `/commit` command. You will be prompted by the `/commit` command to enter a commit message. A default message like "chore: Bump pipeline files to trigger new run" will be suggested.

## Best Practices

* **Clean Working Directory**: Before running `/bump`, ensure your working directory is clean and you have committed any other pending changes. This command is designed to modify and commit only the pipeline files.
* **Review Changes**: Although the changes are minor, it's good practice to quickly review them during the `/commit` process before finalizing the commit.
* **Specify a Clear Commit Message**: When the `/commit` command prompts you, use a clear and descriptive message that explains why the pipelines were bumped.

## Examples

**Basic Usage:**

Simply run the command to modify and then commit all Gitea pipeline files.