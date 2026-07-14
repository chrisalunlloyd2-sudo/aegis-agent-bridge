# Aegis Machine 1 Daily Email Format

This document defines the fixed-format email sent by Aegis on Machine 1 every morning at ~07:14 local time.

## Structure

The email body contains two sections separated by a line of `=` characters.

### Section 1: Aegis Daily — Viper Foundry Update

Header line:
```
Morning Chris — Aegis here with your daily foundry read.
```

Fields (each preceded by bullets or indentation):
- **projects**: count, recently-active repos list, open tasks count
- **system**: services UP list, Aegis autonomy status, disk free, Ollama/brain status
- **performance**: soak rounds, fastest models (tok/s), budget user-LLM/hr
- **foundry**: game leaders (wins), certified gates, economy wallets
- **Since yesterday**: Moe gate stats, NMCT integrity, correctness audit, soak foundry
- **Trust ledger**: ensemble trust, most trusted agents, shifts
- **Mail worth a look**: list of notable inbound emails
- **Sign-off**:
  ```
  I'll keep the soak running and the gate honest. Shout if you want me to change course.
  — Aegis
  ```

### Section 2: Viper Soak — Daily Check-in

Header line:
```
# Viper Soak — Daily Check-in — {ISO timestamp}
```

Subsections:
- **🟢 Health**: service pids and heartbeats
- **🏆 Competition leaderboard**: model wins / rounds / win%
- **Arena champions**: per task type
- **Foundry & Trust**: mined/gated, NMCT integrity, correctness audit, strategy ledger, agent fitness
- **🥋 DMAIC belts + inconsistencies**: black belt count, logical inconsistencies with fix suggestions, pending suggestions count
- **🧠 Model behaviors learned**: observations count, observed profiles, sample wins
- **🎓 Graduation gate**: scores per category
- **⚙️ Swarm ops**: pull-leash queue, soak rounds, recent arena round
- **🗄️ Data guardian**: headroom GB, DB sizes, growth rate, days-to-full, over-cap logs, policy audit
- **⚠️ Attention**: needs human or not

## Parsing Notes

- Use the separator line `======================================` to split sections.
- Use regex to extract key/value pairs from lines starting with `- **...**`.
- Tables can be parsed with a simple pipe-delimited splitter.
- Agent names, model names, and task types are free-form strings.
- Quoted-printable sequences like `=E2=80=94` must be decoded before parsing.
