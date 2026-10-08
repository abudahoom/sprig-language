# Learn Sprig

This is a short course for someone who wants to **use** Sprig, not study its
implementation. You do not need prior programming experience. Work through the
numbered programs in `learn/`; each one is a complete file you can run and
change.

## Before you begin

Open a terminal in the repository folder. Check that Sprig works:

```sh
python3 -m spriglang -c 'print("Sprig is ready!")'
```

Run any lesson with:

```sh
python3 -m spriglang learn/01_hello.sprig
```

After running a lesson, open the file, make one small change, save it, and run
it again. Experimenting is the fastest way to learn.

## Lesson 1: output and variables

Start with `learn/01_hello.sprig`.

```sprig
let name = "Maya"
let language = "Sprig"
print("Hello, " + name + "!")
print("You are learning", language)
```

`let` creates a named value. Text goes inside quotes. `print` displays values,
and `+` joins two strings.

Try this:

1. Change `"Maya"` to your name.
2. Add `let day = "Saturday"`.
3. Print a sentence that uses `day`.

## Lesson 2: values and calculations

Run `learn/02_values_and_math.sprig`.

```sprig
let price = 12.5
let quantity = 4
let total = price * quantity
print("Total:", total)
```

Sprig values include numbers, strings, `true`, `false`, `none`, lists, and
functions. The arithmetic operators are `+`, `-`, `*`, `/`, and `%` (remainder).

Try changing the price and quantity. Then calculate a 10% discount:

```sprig
let discounted = total * 0.9
```

## Lesson 3: decisions

Run `learn/03_decisions.sprig`.

```sprig
if temperature >= 30 {
    print("It is hot.")
} else if temperature <= 10 {
    print("It is cold.")
} else {
    print("The weather is mild.")
}
```

The condition after `if` is tested first. Only one matching block runs.
Comparison operators are `==`, `!=`, `<`, `<=`, `>`, and `>=`. Combine tests
with `and`, `or`, and `not`.

Try adding a boolean named `is_raining`, then print `"Take an umbrella"` when
it is true.

## Lesson 4: repetition

Run `learn/04_loops.sprig`.

Use `for` when you have a group of values:

```sprig
for color in ["red", "green", "blue"] {
    print(color)
}
```

Use `while` when you want to continue until a condition changes:

```sprig
let countdown = 3
while countdown > 0 {
    print(countdown)
    countdown = countdown - 1
}
```

Try changing `range(1, 6)` in the lesson to `range(2, 11, 2)`. This produces
the even numbers from 2 through 10.

## Lesson 5: functions

Run `learn/05_functions.sprig`.

```sprig
fn area(width, height) {
    return width * height
}

print(area(6, 4))
```

A function packages reusable behavior. Inputs are called parameters. `return`
sends a result back to the caller.

Write a function named `minutes_to_seconds(minutes)` that returns `minutes *
60`, then call it with `5`.

## Lesson 6: lists

Run `learn/06_lists.sprig`.

```sprig
let tasks = ["learn variables", "learn loops", "build a project"]
print(tasks[0])
tasks[1] = "practice loops"

for task in tasks {
    print("-", task)
}
```

List indexes begin at zero. `len(tasks)` gives the number of items. A list can
hold values of different kinds, although using similar values is often easier
to understand.

Try adding a fourth task and printing the last item by its index.

## Lesson 7: closures

Run `learn/07_closures.sprig` after you are comfortable with functions.

A function declared inside another function remembers the surrounding
variables. That remembered environment is called a closure. The lesson builds
two independent counters to show that each closure keeps its own state.

Closures are useful, but they are not required for ordinary Sprig programs. It
is fine to return to this lesson later.

## Lesson 8: your first project

`learn/08_mini_project.sprig` is a complete score report. It combines variables,
lists, loops, conditions, and functions.

This is the best answer to “what code should I put in my Sprig program?”:

1. Put your data near the top in variables and lists.
2. Write small functions that answer one question each.
3. Loop over the data to calculate or display results.
4. Use `if` to select different behavior.
5. Print a clear final result.

For a new project, copy the lesson:

```sh
cp learn/08_mini_project.sprig my_project.sprig
python3 -m spriglang my_project.sprig
```

Ideas for changing it:

- Replace school scores with game scores.
- Track daily temperatures and report the hottest one.
- Store expenses and calculate their total and average.
- Store distances and convert each from kilometers to miles.
- Make a quiz answer checker using two lists and indexed assignment.

## Practice exercises

Open `learn/exercises.sprig`. Each `TODO` describes one piece of code to write.
Run the file after every change. If you get stuck, compare it with
`learn/solutions.sprig`.

Do not copy every solution immediately. Give yourself five minutes to try,
read the closest lesson again, and use the error message as a clue.

## Reading errors

A Sprig error points at the part of the program it could not understand or run:

```text
practice.sprig:2:7: runtime error: undefined variable 'score'
  print(score)
        ^
```

Read the last part first: `score` has not been created in the current scope.
Then look at the source line and caret. Common fixes are:

- create a variable with `let` before using it;
- check spelling and capitalization;
- close every `(`, `[`, string quote, and `{`;
- put a newline or semicolon between statements;
- pass the expected number of function arguments.

You can inspect how Sprig understands a program:

```sh
python3 -m spriglang --tokens learn/01_hello.sprig
python3 -m spriglang --ast learn/01_hello.sprig
python3 -m spriglang --bytecode learn/01_hello.sprig
```

## Where to go next

After the course:

- explore the larger programs in `examples/`;
- invent a small project using a list of numbers or strings;
- read `docs/ARCHITECTURE.md` if you want to understand how Sprig itself works;
- add a language feature such as `break`, `continue`, or a new built-in.

The goal is not to memorize every rule. The goal is to write, run, change, and
understand one small program at a time.

