# Primal-Page

This is the tooling for working with the primerschemes index

## Commands

```build-index```: Build an index.json file from all schemes in the directory    

```create```: Add a scheme version into the repo

```modify```: Modify an existing scheme's metadata (info.json) 

- ```add-author```

- ```remove-author```

- ```add-citation```

- ```remove-citation```

- ```change-status```

```remove```: Remove a scheme from the repo   


## Info.json schemma

The main purpose of info.json is to store vital metadata, which is parsed into the repo-manifest. 

### Create 

The create command has two main modes of use. 
- Where the scheme directory is provided, and used to parse; --primerbed, --reference, --configpath, --algorithmversion.
- The options are provided via the CLI

If a field cannot be parsed via the scheme directory, it will require it to be spesified via the CLI.
- CLI args always override the parsed args.

