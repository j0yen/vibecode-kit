# SETUP — connect your evidence sources and workspace

This page turns a fresh vibecode-kit install into a grounded, versioned
workspace: `/dream` cites real Jira tickets, Confluence pages, and GitHub
code instead of guessing, and everything you draft or build is backed up to
a private GitHub repo you own.

**How to use this page:** each numbered section contains one prompt block.
Copy the whole block, paste it into Claude Code, and follow along — Claude
runs the commands, walks you through any browser logins, and verifies the
result before telling you it worked. You never need to run a command
yourself; when a step needs an interactive login, Claude will ask you to
type it with a `!` prefix (for example `! gh auth login`), which runs it
inside your session so Claude can see the outcome.

Do them in order. 1 and 2 are required; 3 grounds `/dream`; 4 and 5 are
optional extras.

---

## 1. GitHub CLI — versioning backbone (required)

```text
Set up the GitHub CLI for me.

1. Check whether `gh` is installed (`gh --version`). If it is missing,
   install it: `brew install gh` on macOS, or on Ubuntu/Debian follow the
   official apt instructions at https://github.com/cli/cli/blob/trunk/docs/install_linux.md
   (fetch that page if you need the current steps).
2. Check `gh auth status`. If I am not logged in, tell me to type
   `! gh auth login` and guide me through it — I will pick GitHub.com,
   HTTPS, and login with a web browser. Wait for me to finish.
3. Verify by running `gh api user --jq .login` and greet me by my GitHub
   username.
4. Make sure `git config --global user.name` and `user.email` are set; if
   not, ask me for them and set them.

When everything passes, say exactly what works and what my GitHub username
is. If anything fails, show me the error and fix it before moving on.
```

## 2. Your private PRD workspace repo (required)

Everything `/dream` drafts and `/build` produces gets committed here and
pushed to a private repo only you (and whoever you invite) can see.

```text
Create my private PRD workspace and wire it to GitHub.

1. Work out my PRD home the same way /dream does: use $DREAM_PRD_DIR if
   set, else ~/Documents/PRDs/ if it exists, else create ./PRDs under my
   home directory and tell me where you put it.
2. If that directory is not already a git repo, `git init` it and make an
   initial commit (create a one-line README.md naming it as my PRD
   workspace if it is empty).
3. If it has no origin remote: run `gh repo create prd-workspace --private
   --source . --remote origin --push` (adjust the name if I already have a
   repo called that — ask me first).
4. Verify: `git remote -v` shows origin, and `gh repo view --json
   visibility` says PRIVATE. Show me the repo URL.

From now on /dream and /build will commit and push here automatically —
that is built into the skills, nothing else to configure. If any step
fails, show me the error and stop rather than working around it.
```

## 3. Atlassian access — ground /dream in Jira and Confluence

Once connected, `/dream` automatically discovers these tools and cites
real tickets and pages as evidence in every PRD. No connection means
`/dream` still works — it just relies on what you paste in.

```text
Connect Claude Code to Atlassian (Jira + Confluence) via MCP.

1. Run: claude mcp add --transport sse atlassian https://mcp.atlassian.com/v1/sse
   If the CLI rejects the sse transport, retry with --transport http.
2. Tell me to type /mcp, pick "atlassian", and complete the browser OAuth
   login with my Atlassian work account. Wait for me to say it is done.
3. Verify with a real read: search Jira for one issue updated in the last
   30 days in a project I name, and fetch its summary. Then fetch the
   title of one Confluence page I name (or any page you can find).
4. Tell me exactly which tools are now available and confirm that /dream
   will discover them automatically on its next run.

If the OAuth flow fails or no tools appear, show me the error — do not
mark this done without the step-3 verification reads succeeding.
```

## 4. Atlassian CLI (optional — bulk operations)

The MCP connection covers grounding. Install `acli` only if you also want
Claude to file or edit Jira issues in bulk from the terminal.

```text
Install and authenticate the Atlassian CLI (acli).

1. Fetch the current install instructions for my OS from
   https://developer.atlassian.com/cloud/acli/guides/install-acli/ and
   follow them. Verify with `acli --version`.
2. Tell me to type `! acli jira auth login` and guide me through the
   browser flow. Wait for me.
3. Verify with a real read: `acli jira workitem search` for one issue in
   a project I name, and show me its key and summary.

If install or auth fails, show me the exact error before trying anything
else.
```

## 5. GitHub MCP server (optional — richer code grounding)

The `gh` CLI from step 1 already lets Claude search and read code for
grounding. Add the GitHub MCP server only if you want native MCP tools
for issues, PRs, and code search as well.

```text
Connect Claude Code to the GitHub MCP server.

1. Run: claude mcp add --transport http github https://api.githubcopilot.com/mcp/
2. Tell me to type /mcp, pick "github", and complete the browser OAuth.
   Wait for me to say it is done.
3. Verify with a real read: search for one repository I name and fetch
   its description via the MCP tools (not the gh CLI).
4. List the GitHub MCP tools now available.

If auth fails, remind me the gh CLI from step 1 already covers most
grounding and this server is optional.
```

---

## Security notes

- Grounding is **read-only**: `/dream` reads Jira, Confluence, and code to
  cite evidence. It never writes to Atlassian without asking you first,
  and nothing in this kit pushes to your company's GitHub organization.
- Your PRD workspace repo is **private by default**. Keep it that way —
  PRDs quote internal tickets and customer signals. Invite specific
  colleagues rather than making it public.
- Credentials live where the official tools put them (gh keyring, MCP
  OAuth tokens). Never paste tokens or passwords into a PRD or a prompt.

## Platform notes

- macOS and Linux are tested. Windows should work via the same tools
  (gh, git, uv all ship Windows builds) but has not been through a pilot —
  if you are the first, tell Joe what breaks.
- Scheduled/background runs may lack the interactive MCP logins from
  steps 3 and 5 — that is expected; `/dream` degrades to ungrounded mode
  rather than failing.
