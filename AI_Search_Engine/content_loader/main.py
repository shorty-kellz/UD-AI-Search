#!/usr/bin/env python3
"""
Content Loader Main - Simple pipeline orchestrator
Run different content ingestion pipelines easily
"""

import sys
from pathlib import Path

# Add content_loader to path
content_loader_path = Path(__file__).parent
sys.path.insert(0, str(content_loader_path))

def run_fast_fact_pipeline():
    """Run FastFact ingestion pipeline"""
    print("🚀 Starting FastFact Pipeline...")
    print("=" * 50)
    
    try:
        # Add backend to path for imports
        backend_path = Path(__file__).parent.parent / "backend"
        sys.path.insert(0, str(backend_path))
        
        # Import the ingestion module
        import ingest_fast_facts
        FastFactIngestion = ingest_fast_facts.FastFactIngestion
        
        # Path to FastFact files
        input_folder = Path(__file__).parent.parent / "data" / "fast_facts_raw"
        
        if not input_folder.exists():
            print(f"❌ Error: FastFact folder not found: {input_folder}")
            print("Please make sure your FastFact MHTML files are in the data/fast_facts_raw folder")
            return False
        
        # Initialize and run ingestion
        ingestion = FastFactIngestion()
        stats = ingestion.process_folder(str(input_folder))
        
        # Show final summary
        print("\n" + "=" * 50)
        print("🎉 FASTFACT PIPELINE COMPLETE!")
        print("=" * 50)
        print(f"✅ Processed: {stats['processed']}")
        print(f"⏭ Skipped: {stats['skipped']}")
        print(f"❌ Errors: {stats['errors']}")
        
        if stats['errors'] > 0:
            print("\n⚠️  Some errors occurred. Check the output above.")
            return False
        else:
            print("\n✅ All FastFact files processed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error running FastFact pipeline: {e}")
        return False

def run_ud_content_pipeline():
    """Run UD Content ingestion pipeline (placeholder)"""
    print("🚀 Starting UD Content Pipeline...")
    print("=" * 50)
    print("⚠️  UD Content pipeline not yet implemented")
    print("This will be available in a future update")
    return False

def run_textbook_pipeline():
    """Run Textbook ingestion pipeline (placeholder)"""
    print("🚀 Starting Textbook Pipeline...")
    print("=" * 50)
    print("⚠️  Textbook pipeline not yet implemented")
    print("This will be available in a future update")
    return False

def run_taxonomy_pipeline():
    """Run Taxonomy ingestion pipeline"""
    print("🚀 Starting Taxonomy Pipeline...")
    print("=" * 50)
    
    try:
        # Import the taxonomy ingestion module
        import ingest_taxonomy
        
        # Run the taxonomy ingestion
        ingest_taxonomy.main()
        
    except Exception as e:
        print(f"❌ Error running Taxonomy pipeline: {e}")

def show_menu():
    """Show the pipeline selection menu"""
    print("\n" + "=" * 50)
    print("📚 CONTENT LOADER - Pipeline Selector")
    print("=" * 50)
    print("Choose which pipeline to run:")
    print("1. FastFact Pipeline (MHTML files)")
    print("2. UD Content Pipeline (not implemented)")
    print("3. Textbook Pipeline (not implemented)")
    print("4. Taxonomy Pipeline (taxonomy structure)")
    print("5. Exit")
    print("=" * 50)

def main():
    """Main function with interactive menu"""
    print("🎯 Content Loader - Simple Pipeline Orchestrator")
    
    while True:
        show_menu()
        
        try:
            choice = input("Enter your choice (1-5): ").strip()
            
            if choice == "1":
                success = run_fast_fact_pipeline()
                if success:
                    print("\n✅ Pipeline completed successfully!")
                else:
                    print("\n❌ Pipeline completed with errors.")
                
            elif choice == "2":
                run_ud_content_pipeline()
                
            elif choice == "3":
                run_textbook_pipeline()
                
            elif choice == "4":
                run_taxonomy_pipeline()
                
            elif choice == "5":
                print("👋 Goodbye!")
                break
                
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Ask if user wants to run another pipeline
        if choice in ["1", "2", "3", "4"]:
            run_another = input("\nRun another pipeline? (y/n): ").strip().lower()
            if run_another not in ["y", "yes"]:
                print("👋 Goodbye!")
                break

if __name__ == "__main__":
    main() 