import { useState, useCallback, useEffect } from "react";
import {
  Button,
  cn,
  Modal,
  ModalContent,
  ModalBody,
  Image,
  useDisclosure,
} from "@heroui/react";
import { Icon } from "@iconify/react/dist/iconify.js";

type ImageGalleryProps = {
  images: Map<string, string>;
};

const ImageGallery = ({ images }: ImageGalleryProps) => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [currentIndex, setCurrentIndex] = useState(0);

  const imageArray = Array.from(images.entries()).map(([id, url]) => ({
    src: url,
    alt: id,
  }));

  const openGallery = (index: number) => {
    setCurrentIndex(index);
    onOpen();
  };

  const goToPrevious = useCallback(() => {
    setCurrentIndex((prev) => (prev === 0 ? imageArray.length - 1 : prev - 1));
  }, [imageArray.length]);

  const goToNext = useCallback(() => {
    setCurrentIndex((prev) => (prev === imageArray.length - 1 ? 0 : prev + 1));
  }, [imageArray.length]);

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          goToPrevious();
          break;
        case "ArrowRight":
          e.preventDefault();
          goToNext();
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, goToPrevious, goToNext, onClose]);

  return (
    <>
      {/* Thumbnail Grid */}
      <div className="mt-2 grid grid-cols-3 gap-2 xs:grid-cols-4 sm:grid-cols-6 md:grid-cols-8 lg:grid-cols-12">
        {imageArray.map((image, index) => (
          <div
            key={image.alt}
            className="relative aspect-square cursor-pointer overflow-hidden rounded-lg"
            onClick={() => openGallery(index)}
          >
            <Image
              src={image.src}
              alt={image.alt}
              className="h-full w-full rounded-lg object-cover transition-transform hover:scale-125"
              classNames={{
                wrapper: "h-full w-full",
                img: "h-full w-full object-cover",
              }}
            />
          </div>
        ))}
      </div>

      {/* Modal Gallery */}
      <Modal
        isOpen={isOpen}
        onClose={onClose}
        size="full"
        hideCloseButton
        classNames={{
          backdrop: "bg-black/90",
          wrapper: "p-0",
          base: "bg-transparent shadow-none m-0",
          body: "p-0",
        }}
      >
        <ModalContent>
          <ModalBody className="relative flex min-h-screen items-center justify-center p-4">
            {/* Close Button */}
            <Button
              isIconOnly
              variant="flat"
              className="absolute right-4 top-4 z-50 bg-black/50 text-white"
              onPress={onClose}
            >
              <Icon icon="heroicons:x-mark" className="h-6 w-6" />
            </Button>

            {/* Navigation Buttons */}
            {imageArray.length > 1 && (
              <>
                <Button
                  isIconOnly
                  variant="flat"
                  className="absolute left-4 top-1/2 z-50 -translate-y-1/2 bg-black/50 text-white"
                  onPress={goToPrevious}
                >
                  <Icon icon="heroicons:chevron-left" className="h-6 w-6" />
                </Button>
                <Button
                  isIconOnly
                  variant="flat"
                  className="absolute right-4 top-1/2 z-50 -translate-y-1/2 bg-black/50 text-white"
                  onPress={goToNext}
                >
                  <Icon icon="heroicons:chevron-right" className="h-6 w-6" />
                </Button>
              </>
            )}

            {/* Main Image */}
            <div className="relative flex max-h-[90vh] max-w-[90vw] items-center justify-center">
              <Image
                src={imageArray[currentIndex]?.src}
                alt={imageArray[currentIndex]?.alt}
                className="max-h-full max-w-full object-contain"
                classNames={{
                  wrapper: "max-w-full max-h-full",
                  img: "max-w-full max-h-full object-contain",
                }}
              />
            </div>

            {/* Thumbnail Strip */}
            {imageArray.length > 1 && (
              <div className="absolute bottom-16 left-1/2 flex max-w-[90vw] -translate-x-1/2 gap-2 overflow-x-auto rounded bg-black/30 p-2">
                {imageArray.map((image, index) => (
                  <button
                    key={image.alt}
                    onClick={() => setCurrentIndex(index)}
                    className={cn(
                      "flex-shrink-0 overflow-hidden border-2 border-transparent transition-all",
                      index === currentIndex
                        ? "z-10 scale-125"
                        : "hover:scale-110",
                    )}
                  >
                    <Image
                      src={image.src}
                      alt={image.alt}
                      className="h-12 w-12 rounded-lg object-cover"
                      classNames={{
                        wrapper: "w-12 h-12",
                        img: "w-12 h-12 object-cover",
                      }}
                    />
                  </button>
                ))}
              </div>
            )}

            {/* Image Counter */}
            {imageArray.length > 1 && (
              <div className="absolute bottom-4 left-1/2 -translate-x-1/2 rounded-full bg-black/50 px-4 py-2">
                <span className="text-sm font-medium text-white">
                  {currentIndex + 1} / {imageArray.length}
                </span>
              </div>
            )}
          </ModalBody>
        </ModalContent>
      </Modal>
    </>
  );
};

export default ImageGallery;
